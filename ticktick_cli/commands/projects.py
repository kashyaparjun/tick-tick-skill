"""Project commands for TickTick CLI."""

import click

from ticktick_cli.config import get_client
from ticktick_cli.output import (
    use_json,
    emit,
    emit_error,
    task_to_dict,
    project_to_dict,
    format_task,
    format_project,
)


@click.group()
def projects():
    """Manage projects."""
    pass


@projects.command("list")
@click.option("-v", "--verbose", is_flag=True, help="Show project details.")
def list_projects(verbose):
    """List all projects."""
    client = get_client()
    project_list = client.state.get("projects", [])

    if use_json():
        emit([project_to_dict(p) for p in project_list])
        return

    if not project_list:
        click.echo("No projects found.")
        return

    for p in project_list:
        click.echo(format_project(p, verbose))


@projects.command("add")
@click.argument("name")
@click.option("--color", default=None, help="Project color (hex, e.g. #ff0000).")
def add_project(name, color):
    """Create a new project."""
    client = get_client()
    kwargs = {}
    if color:
        kwargs["color"] = color
    result = client.project.create(name, **kwargs)

    if use_json():
        emit(project_to_dict(result))
    else:
        click.echo(f"Created project: {result['name']}  (ID: {result['id']})")


@projects.command("delete")
@click.argument("name")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
def delete_project(name, yes):
    """Delete a project by name (also deletes its tasks)."""
    client = get_client()
    proj = _find_project(client, name)
    if not proj:
        emit_error(f"Project '{name}' not found.")
        return
    if not yes and not use_json():
        click.confirm(f"Delete project '{proj['name']}' and all its tasks?", abort=True)
    client.project.delete(proj["id"])

    if use_json():
        emit({"status": "deleted", "name": proj["name"], "id": proj["id"]})
    else:
        click.echo(f"Deleted project: {proj['name']}")


@projects.command("tasks")
@click.argument("name")
@click.option("-v", "--verbose", is_flag=True, help="Show task details.")
def project_tasks(name, verbose):
    """List tasks in a project."""
    client = get_client()
    proj = _find_project(client, name)
    if not proj:
        emit_error(f"Project '{name}' not found.")
        return

    task_list = client.task.get_from_project(proj["id"])

    if use_json():
        emit([task_to_dict(t) for t in task_list])
        return

    if not task_list:
        click.echo(f"No tasks in '{proj['name']}'.")
        return

    for t in task_list:
        click.echo(format_task(t, verbose))


def _find_project(client, name):
    """Find a project by name (case-insensitive)."""
    projects = client.state.get("projects", [])
    name_lower = name.lower()
    for p in projects:
        if p.get("name", "").lower() == name_lower:
            return p
    return None
