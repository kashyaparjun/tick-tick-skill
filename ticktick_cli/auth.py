"""OAuth2 authentication flow with local HTTP server for redirect capture."""

import json
import threading
import time
import webbrowser
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

import click
import requests

from ticktick_cli.config import CONFIG_DIR, TOKEN_CACHE, load_config, save_config

TICKTICK_AUTH_URL = "https://ticktick.com/oauth/authorize"
TICKTICK_TOKEN_URL = "https://ticktick.com/oauth/token"
SCOPE = "tasks:write tasks:read"


class _OAuthCallbackHandler(BaseHTTPRequestHandler):
    """Handles the OAuth redirect and extracts the authorization code."""

    auth_code = None
    error = None

    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)

        if "code" in query:
            _OAuthCallbackHandler.auth_code = query["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(
                b"<html><body><h2>Authentication successful!</h2>"
                b"<p>You can close this tab and return to the terminal.</p></body></html>"
            )
        else:
            _OAuthCallbackHandler.error = query.get("error", ["unknown"])[0]
            self.send_response(400)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(
                b"<html><body><h2>Authentication failed.</h2>"
                b"<p>Check the terminal for details.</p></body></html>"
            )

    def log_message(self, format, *args):
        pass  # suppress HTTP logs


def _exchange_code_for_token(code: str, config: dict) -> dict:
    """Exchange authorization code for access token."""
    resp = requests.post(
        TICKTICK_TOKEN_URL,
        data={
            "client_id": config["client_id"],
            "client_secret": config["client_secret"],
            "code": code,
            "grant_type": "authorization_code",
            "scope": SCOPE,
            "redirect_uri": config["redirect_uri"],
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    resp.raise_for_status()
    token_data = resp.json()

    # Add expiry fields the same way ticktick-py does
    expires_in = token_data.get("expires_in", 0)
    expire_time = time.time() + expires_in
    token_data["expire_time"] = expire_time
    token_data["readable_expire_time"] = datetime.fromtimestamp(
        expire_time, tz=timezone.utc
    ).strftime("%Y-%m-%d %H:%M:%S UTC")

    return token_data


def _save_token(token_data: dict):
    """Write token to the cache file."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    TOKEN_CACHE.write_text(json.dumps(token_data))


def _load_token() -> dict | None:
    """Load cached token if it exists."""
    if not TOKEN_CACHE.exists():
        return None
    try:
        return json.loads(TOKEN_CACHE.read_text())
    except (json.JSONDecodeError, IOError):
        return None


def login():
    """Run the full OAuth2 login flow."""
    config = load_config()
    required = ["client_id", "client_secret", "redirect_uri"]
    missing = [k for k in required if not config.get(k)]

    if missing:
        click.echo("OAuth app not configured yet. Let's set that up first.\n")
        click.echo("Register an app at https://developer.ticktick.com/manage")
        click.echo("Set the redirect URI to http://localhost:8080\n")
        config["client_id"] = click.prompt("OAuth Client ID", default=config.get("client_id", ""))
        config["client_secret"] = click.prompt("OAuth Client Secret", default=config.get("client_secret", ""))
        config["redirect_uri"] = click.prompt(
            "Redirect URI", default=config.get("redirect_uri", "http://localhost:8080")
        )

    if not config.get("username") or not config.get("password"):
        click.echo("\nTickTick account credentials (needed for the internal API):")
        config["username"] = click.prompt("Email", default=config.get("username", ""))
        config["password"] = click.prompt("Password", hide_input=True)

    save_config(config)

    # Parse the redirect URI to determine local server port
    parsed = urlparse(config["redirect_uri"])
    port = parsed.port or 8080

    # Build authorization URL
    auth_url = (
        f"{TICKTICK_AUTH_URL}"
        f"?client_id={config['client_id']}"
        f"&scope={SCOPE.replace(' ', '+')}"
        f"&response_type=code"
        f"&redirect_uri={config['redirect_uri']}"
        f"&state=ticktick-cli"
    )

    # Reset handler state
    _OAuthCallbackHandler.auth_code = None
    _OAuthCallbackHandler.error = None

    # Start local server to capture the redirect
    server = HTTPServer(("127.0.0.1", port), _OAuthCallbackHandler)
    server_thread = threading.Thread(target=server.handle_request, daemon=True)
    server_thread.start()

    click.echo(f"\nOpening browser for authorization...")
    click.echo(f"If the browser doesn't open, visit:\n{auth_url}\n")
    webbrowser.open(auth_url)

    click.echo("Waiting for authorization...")
    server_thread.join(timeout=120)
    server.server_close()

    if _OAuthCallbackHandler.error:
        click.echo(f"Authorization failed: {_OAuthCallbackHandler.error}", err=True)
        return False

    if not _OAuthCallbackHandler.auth_code:
        click.echo("Timed out waiting for authorization.", err=True)
        return False

    click.echo("Authorization received. Exchanging for token...")

    try:
        token_data = _exchange_code_for_token(_OAuthCallbackHandler.auth_code, config)
        _save_token(token_data)
        click.echo(f"Logged in successfully!")
        click.echo(f"Token expires: {token_data.get('readable_expire_time', 'unknown')}")
        return True
    except requests.HTTPError as e:
        click.echo(f"Token exchange failed: {e}", err=True)
        return False


def logout():
    """Clear cached tokens."""
    removed = False
    if TOKEN_CACHE.exists():
        TOKEN_CACHE.unlink()
        removed = True

    if removed:
        click.echo("Logged out. Token cleared.")
    else:
        click.echo("No active session found.")


def status():
    """Show current authentication status."""
    config = load_config()
    token = _load_token()

    if not config.get("client_id"):
        click.echo("Status: not configured")
        click.echo("Run: tt auth signin")
        return

    click.echo(f"User:         {config.get('username', 'not set')}")
    click.echo(f"Client ID:    {config.get('client_id', 'not set')[:8]}...")
    click.echo(f"Redirect URI: {config.get('redirect_uri', 'not set')}")
    click.echo(f"Config:       {CONFIG_DIR}")

    if not token:
        click.echo("Token:        none (run: tt auth login)")
        return

    expire_time = token.get("expire_time", 0)
    now = time.time()
    if now >= expire_time - 60:
        click.echo("Token:        expired (run: tt auth login)")
    else:
        remaining_days = int((expire_time - now) / 86400)
        click.echo(f"Token:        valid ({remaining_days} days remaining)")
        click.echo(f"Expires:      {token.get('readable_expire_time', 'unknown')}")
