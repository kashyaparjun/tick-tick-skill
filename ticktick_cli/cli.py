"""Main CLI entry point for TickTick CLI."""

import click

from ticktick_cli.commands.tasks import tasks
from ticktick_cli.commands.projects import projects
from ticktick_cli.commands.tags import tags
from ticktick_cli.auth import login, logout, status


@click.group()
@click.version_option(version="0.1.0")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON (for LLM/script consumption).")
@click.pass_context
def cli(ctx, json_output):
    """TickTick CLI - manage your tasks from the terminal."""
    ctx.ensure_object(dict)
    ctx.params["json_output"] = json_output


@cli.group()
def auth():
    """Authenticate with TickTick."""
    pass


@auth.command()
def signin():
    """Log in to TickTick (opens browser for OAuth)."""
    login()


@auth.command()
def signout():
    """Log out and clear stored tokens."""
    logout()


@auth.command("status")
def auth_status():
    """Show current authentication status."""
    status()


cli.add_command(tasks)
cli.add_command(projects)
cli.add_command(tags)


if __name__ == "__main__":
    cli()
