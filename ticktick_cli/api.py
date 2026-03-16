"""Direct client for the TickTick Open API v1."""

import json
import sys
import time

import click
import requests

from ticktick_cli.config import CONFIG_DIR, TOKEN_CACHE, load_config

BASE_URL = "https://api.ticktick.com/open/v1"


class TickTickAPI:
    """Thin wrapper around the TickTick Open API using OAuth2 Bearer token."""

    def __init__(self, access_token: str):
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        })

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        resp = self.session.request(method, f"{BASE_URL}{path}", **kwargs)
        resp.raise_for_status()
        return resp

    # ── Projects ──────────────────────────────────────────────────────────

    def get_projects(self) -> list[dict]:
        return self._request("GET", "/project").json()

    def get_project(self, project_id: str) -> dict:
        return self._request("GET", f"/project/{project_id}").json()

    def create_project(self, data: dict) -> dict:
        return self._request("POST", "/project", json=data).json()

    def delete_project(self, project_id: str):
        self._request("DELETE", f"/project/{project_id}")

    def get_project_with_tasks(self, project_id: str) -> dict:
        return self._request("GET", f"/project/{project_id}/data").json()

    # ── Tasks ─────────────────────────────────────────────────────────────

    def create_task(self, data: dict) -> dict:
        return self._request("POST", "/task", json=data).json()

    def update_task(self, task_id: str, data: dict) -> dict:
        return self._request("POST", f"/task/{task_id}", json=data).json()

    def get_task(self, project_id: str, task_id: str) -> dict:
        return self._request("GET", f"/task/{project_id}/{task_id}").json()

    def complete_task(self, project_id: str, task_id: str):
        self._request("POST", f"/project/{project_id}/task/{task_id}/complete")

    def delete_task(self, project_id: str, task_id: str):
        self._request("DELETE", f"/project/{project_id}/task/{task_id}")


def get_api() -> TickTickAPI:
    """Load token and return an authenticated API client."""
    config = load_config()
    required = ["client_id", "client_secret", "redirect_uri"]
    missing = [k for k in required if not config.get(k)]

    if missing:
        click.echo("Not configured. Run: tt auth signin", err=True)
        sys.exit(1)

    if not TOKEN_CACHE.exists():
        click.echo("Not authenticated. Run: tt auth signin", err=True)
        sys.exit(1)

    try:
        token_data = json.loads(TOKEN_CACHE.read_text())
    except (json.JSONDecodeError, IOError):
        click.echo("Token file corrupt. Run: tt auth signin", err=True)
        sys.exit(1)

    expire_time = token_data.get("expire_time", 0)
    if time.time() >= expire_time - 60:
        click.echo("Token expired. Run: tt auth signin", err=True)
        sys.exit(1)

    access_token = token_data.get("access_token")
    if not access_token:
        click.echo("No access token found. Run: tt auth signin", err=True)
        sys.exit(1)

    return TickTickAPI(access_token)
