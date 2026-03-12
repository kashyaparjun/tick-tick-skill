"""Configuration management for TickTick CLI."""

import json
import sys
from pathlib import Path

import click

CONFIG_DIR = Path.home() / ".config" / "ticktick-cli"
CONFIG_FILE = CONFIG_DIR / "config.json"
TOKEN_CACHE = CONFIG_DIR / ".token-oauth"


def load_config() -> dict:
    if not CONFIG_FILE.exists():
        return {}
    return json.loads(CONFIG_FILE.read_text())


def save_config(config: dict):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(config, indent=2))


def get_client():
    """Create and return an authenticated TickTickClient."""
    config = load_config()
    required = ["username", "password", "client_id", "client_secret", "redirect_uri"]
    missing = [k for k in required if not config.get(k)]

    if missing:
        click.echo("Not configured. Run: tt auth signin")
        sys.exit(1)

    if not TOKEN_CACHE.exists():
        click.echo("Not authenticated. Run: tt auth signin")
        sys.exit(1)

    try:
        from ticktick.api import TickTickClient
        from ticktick.oauth2 import OAuth2

        auth = OAuth2(
            client_id=config["client_id"],
            client_secret=config["client_secret"],
            redirect_uri=config["redirect_uri"],
            cache_path=str(TOKEN_CACHE),
        )
        return TickTickClient(config["username"], config["password"], auth)
    except Exception as e:
        click.echo(f"Authentication failed: {e}", err=True)
        click.echo("Try: tt auth login")
        sys.exit(1)
