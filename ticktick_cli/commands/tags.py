"""Tag commands for TickTick CLI.

Note: The TickTick Open API v1 does not have tag endpoints.
Tag operations are not supported at this time.
"""

import click

from ticktick_cli.output import emit_error


@click.group()
def tags():
    """Manage tags (not yet supported by TickTick Open API)."""
    pass


def _unsupported():
    # TickTick Open API (open/v1) does not currently expose tag management.
    # The previous implementation relied on TickTick's internal API via
    # ticktick-py, which is unstable and can fail with HTTP 405 loops.
    emit_error("Tags are not supported by TickTick Open API; this CLI does not support `tt tags` at the moment.")


@tags.command("list")
def list_tags():
    """List all tags."""
    _unsupported()


@tags.command("add")
@click.argument("label")
@click.option("--color", default=None, help="Tag color (hex).")
@click.option("--parent", default=None, help="Parent tag label.")
def add_tag(label, color, parent):
    """Create a new tag."""
    _unsupported()


@tags.command("delete")
@click.argument("label")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
def delete_tag(label, yes):
    """Delete a tag."""
    _unsupported()


@tags.command("rename")
@click.argument("old_name")
@click.argument("new_name")
def rename_tag(old_name, new_name):
    """Rename a tag."""
    _unsupported()
