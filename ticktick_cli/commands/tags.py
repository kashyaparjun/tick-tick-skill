"""Tag commands for TickTick CLI."""

import click

from ticktick_cli.config import get_client
from ticktick_cli.output import use_json, emit, emit_error, tag_to_dict


@click.group()
def tags():
    """Manage tags."""
    pass


@tags.command("list")
@click.option("-v", "--verbose", is_flag=True, help="Show tag details.")
def list_tags(verbose):
    """List all tags."""
    client = get_client()
    tag_list = client.state.get("tags", [])

    if use_json():
        emit([tag_to_dict(t) for t in tag_list])
        return

    if not tag_list:
        click.echo("No tags found.")
        return

    for t in tag_list:
        label = t.get("label", t.get("name", "Untitled"))
        line = f"  {label}"
        if verbose:
            color = t.get("color")
            if color:
                line += f"  (color: {color})"
            parent = t.get("parent")
            if parent:
                line += f"  (parent: {parent})"
        click.echo(line)


@tags.command("add")
@click.argument("label")
@click.option("--color", default=None, help="Tag color (hex).")
@click.option("--parent", default=None, help="Parent tag label.")
def add_tag(label, color, parent):
    """Create a new tag."""
    client = get_client()
    kwargs = {}
    if color:
        kwargs["color"] = color
    if parent:
        kwargs["parent"] = parent
    result = client.tag.create(label, **kwargs)

    if use_json():
        emit(tag_to_dict(result))
    else:
        click.echo(f"Created tag: {result.get('label', result.get('name', label))}")


@tags.command("delete")
@click.argument("label")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
def delete_tag(label, yes):
    """Delete a tag."""
    if not yes and not use_json():
        click.confirm(f"Delete tag '{label}'?", abort=True)
    client = get_client()
    client.tag.delete(label)

    if use_json():
        emit({"status": "deleted", "label": label})
    else:
        click.echo(f"Deleted tag: {label}")


@tags.command("rename")
@click.argument("old_name")
@click.argument("new_name")
def rename_tag(old_name, new_name):
    """Rename a tag."""
    client = get_client()
    client.tag.rename(old_name, new_name)

    if use_json():
        emit({"status": "renamed", "old": old_name, "new": new_name})
    else:
        click.echo(f"Renamed '{old_name}' -> '{new_name}'")
