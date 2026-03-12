"""Task commands for TickTick CLI."""

from datetime import datetime, timedelta

import click

from ticktick_cli.config import get_client
from ticktick_cli.output import (
    PRIORITY_MAP,
    use_json,
    emit,
    emit_error,
    task_to_dict,
    format_task,
)


@click.group()
def tasks():
    """Manage tasks."""
    pass


@tasks.command("list")
@click.option("-p", "--project", default=None, help="Filter by project name.")
@click.option("-v", "--verbose", is_flag=True, help="Show task details.")
@click.option("--priority", type=click.Choice(["low", "medium", "high"]), help="Filter by priority.")
def list_tasks(project, verbose, priority):
    """List all tasks."""
    client = get_client()

    if project:
        proj = _find_project(client, project)
        if not proj:
            emit_error(f"Project '{project}' not found.")
            return
        task_list = client.task.get_from_project(proj["id"])
    else:
        task_list = client.state.get("tasks", [])

    if priority:
        pri_val = PRIORITY_MAP[priority]
        task_list = [t for t in task_list if t.get("priority") == pri_val]

    if use_json():
        emit([task_to_dict(t) for t in task_list])
        return

    if not task_list:
        click.echo("No tasks found.")
        return

    for t in task_list:
        click.echo(format_task(t, verbose))


@tasks.command("add")
@click.argument("title")
@click.option("-p", "--project", default=None, help="Project name.")
@click.option("--priority", type=click.Choice(["none", "low", "medium", "high"]), default="none")
@click.option("--due", default=None, help="Due date (YYYY-MM-DD).")
@click.option("--note", default=None, help="Task description/content.")
@click.option("--all-day", is_flag=True, help="Mark as all-day task.")
def add_task(title, project, priority, due, note, all_day):
    """Create a new task."""
    client = get_client()

    kwargs = {"title": title, "priority": PRIORITY_MAP[priority]}

    if project:
        proj = _find_project(client, project)
        if not proj:
            emit_error(f"Project '{project}' not found.")
            return
        kwargs["projectId"] = proj["id"]

    if due:
        try:
            due_dt = datetime.strptime(due, "%Y-%m-%d")
            kwargs["dueDate"] = due_dt
            kwargs["allDay"] = all_day or True
        except ValueError:
            emit_error("Invalid date format. Use YYYY-MM-DD.")
            return

    if note:
        kwargs["content"] = note

    task = client.task.builder(**kwargs)
    result = client.task.create(task)

    if use_json():
        emit(task_to_dict(result))
    else:
        click.echo(f"Created: {result['title']}  (ID: {result['id']})")


@tasks.command("done")
@click.argument("task_id")
def complete_task(task_id):
    """Mark a task as complete by ID."""
    client = get_client()
    task = client.get_by_id(task_id)
    if not task:
        emit_error("Task not found.")
        return
    client.task.complete(task)

    if use_json():
        emit({"status": "completed", "id": task_id, "title": task["title"]})
    else:
        click.echo(f"Completed: {task['title']}")


@tasks.command("delete")
@click.argument("task_id")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
def delete_task(task_id, yes):
    """Delete a task by ID."""
    client = get_client()
    task = client.get_by_id(task_id)
    if not task:
        emit_error("Task not found.")
        return
    if not yes and not use_json():
        click.confirm(f"Delete '{task['title']}'?", abort=True)
    client.task.delete(task)

    if use_json():
        emit({"status": "deleted", "id": task_id, "title": task["title"]})
    else:
        click.echo(f"Deleted: {task['title']}")


@tasks.command("update")
@click.argument("task_id")
@click.option("--title", default=None, help="New title.")
@click.option("--priority", type=click.Choice(["none", "low", "medium", "high"]), default=None)
@click.option("--due", default=None, help="New due date (YYYY-MM-DD).")
@click.option("--note", default=None, help="New description/content.")
def update_task(task_id, title, priority, due, note):
    """Update an existing task by ID."""
    client = get_client()
    task = client.get_by_id(task_id)
    if not task:
        emit_error("Task not found.")
        return

    if title:
        task["title"] = title
    if priority:
        task["priority"] = PRIORITY_MAP[priority]
    if due:
        try:
            due_dt = datetime.strptime(due, "%Y-%m-%d")
            task["dueDate"] = client.task.dates(due_dt)["dueDate"]
        except ValueError:
            emit_error("Invalid date format. Use YYYY-MM-DD.")
            return
    if note:
        task["content"] = note

    result = client.task.update(task)

    if use_json():
        emit(task_to_dict(result))
    else:
        click.echo(f"Updated: {result['title']}")


@tasks.command("search")
@click.argument("query")
@click.option("-v", "--verbose", is_flag=True, help="Show task details.")
def search_tasks(query, verbose):
    """Search tasks by title."""
    client = get_client()
    all_tasks = client.state.get("tasks", [])
    query_lower = query.lower()
    matches = [t for t in all_tasks if query_lower in t.get("title", "").lower()]

    if use_json():
        emit([task_to_dict(t) for t in matches])
        return

    if not matches:
        click.echo("No matching tasks.")
        return

    for t in matches:
        click.echo(format_task(t, verbose))


@tasks.command("move")
@click.argument("task_id")
@click.argument("project_name")
def move_task(task_id, project_name):
    """Move a task to a different project."""
    client = get_client()
    task = client.get_by_id(task_id)
    if not task:
        emit_error("Task not found.")
        return
    proj = _find_project(client, project_name)
    if not proj:
        emit_error(f"Project '{project_name}' not found.")
        return
    client.task.move(task, proj["id"])

    if use_json():
        emit({"status": "moved", "id": task_id, "title": task["title"], "project": proj["name"]})
    else:
        click.echo(f"Moved '{task['title']}' to '{proj['name']}'")


@tasks.command("due")
@click.option("--days", default=7, type=int, help="Number of days ahead (default: 7).")
@click.option("-v", "--verbose", is_flag=True, help="Show task details.")
def due_tasks(days, verbose):
    """Show tasks due within N days."""
    client = get_client()
    all_tasks = client.state.get("tasks", [])
    now = datetime.now()
    cutoff = now + timedelta(days=days)

    due_list = []
    for t in all_tasks:
        due = t.get("dueDate")
        if due:
            try:
                due_dt = datetime.fromisoformat(due.replace("Z", "+00:00"))
                if due_dt.replace(tzinfo=None) <= cutoff:
                    due_list.append(t)
            except (ValueError, TypeError):
                pass

    due_list.sort(key=lambda t: t.get("dueDate", ""))

    if use_json():
        emit([task_to_dict(t) for t in due_list])
        return

    if not due_list:
        click.echo(f"No tasks due in the next {days} days.")
        return

    for t in due_list:
        click.echo(format_task(t, verbose))


def _find_project(client, name):
    """Find a project by name (case-insensitive)."""
    projects = client.state.get("projects", [])
    name_lower = name.lower()
    for p in projects:
        if p.get("name", "").lower() == name_lower:
            return p
    return None
