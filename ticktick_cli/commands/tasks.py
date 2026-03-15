"""Task commands for TickTick CLI."""

from datetime import datetime, timedelta

import click

from ticktick_cli.config import get_open_api
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
    api = get_open_api()
    projects = _get_projects(api)
    if projects is None:
        return

    if project:
        proj = _find_project(projects, project)
        if not proj:
            emit_error(f"Project '{project}' not found.")
            return
        task_list = _get_tasks_for_project(api, proj["id"])
    else:
        task_list = _get_all_tasks(api, projects)

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
    api = get_open_api()
    projects = _get_projects(api)
    if projects is None:
        return

    payload = {"title": title, "priority": PRIORITY_MAP[priority]}

    if project:
        proj = _find_project(projects, project)
        if not proj:
            emit_error(f"Project '{project}' not found.")
            return
        payload["projectId"] = proj["id"]

    if due:
        try:
            datetime.strptime(due, "%Y-%m-%d")
        except ValueError:
            emit_error("Invalid date format. Use YYYY-MM-DD.")
            return
        payload["dueDate"] = _ticktick_due_datetime(due)
        payload["isAllDay"] = True if all_day else True

    if note:
        payload["content"] = note

    try:
        result = api.post("/task", json=payload)
    except Exception as e:
        emit_error(str(e))
        return

    if use_json():
        emit(task_to_dict(result))
    else:
        click.echo(f"Created: {result['title']}  (ID: {result['id']})")


@tasks.command("done")
@click.argument("task_id")
@click.argument("project_id", required=False)
def complete_task(task_id, project_id):
    """Mark a task as complete by ID."""
    api = get_open_api()
    task, pid = _resolve_task(api, task_id, project_id)
    if not task:
        return
    try:
        api.post(f"/project/{pid}/task/{task_id}/complete", json={})
    except Exception as e:
        emit_error(str(e))
        return

    if use_json():
        emit({"status": "completed", "id": task_id, "title": task["title"]})
    else:
        click.echo(f"Completed: {task['title']}")


@tasks.command("delete")
@click.argument("task_id")
@click.argument("project_id", required=False)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
def delete_task(task_id, project_id, yes):
    """Delete a task by ID."""
    api = get_open_api()
    task, pid = _resolve_task(api, task_id, project_id)
    if not task:
        return
    if not yes and not use_json():
        click.confirm(f"Delete '{task['title']}'?", abort=True)
    try:
        api.delete(f"/project/{pid}/task/{task_id}")
    except Exception as e:
        emit_error(str(e))
        return

    if use_json():
        emit({"status": "deleted", "id": task_id, "title": task["title"]})
    else:
        click.echo(f"Deleted: {task['title']}")


@tasks.command("update")
@click.argument("task_id")
@click.argument("project_id", required=False)
@click.option("--title", default=None, help="New title.")
@click.option("--priority", type=click.Choice(["none", "low", "medium", "high"]), default=None)
@click.option("--due", default=None, help="New due date (YYYY-MM-DD).")
@click.option("--note", default=None, help="New description/content.")
def update_task(task_id, project_id, title, priority, due, note):
    """Update an existing task by ID."""
    api = get_open_api()
    task, pid = _resolve_task(api, task_id, project_id)
    if not task:
        return

    payload = {"id": task_id, "projectId": pid}

    if title:
        payload["title"] = title
    if priority:
        payload["priority"] = PRIORITY_MAP[priority]
    if due:
        try:
            datetime.strptime(due, "%Y-%m-%d")
        except ValueError:
            emit_error("Invalid date format. Use YYYY-MM-DD.")
            return
        payload["dueDate"] = _ticktick_due_datetime(due)
        payload["isAllDay"] = True
    if note:
        payload["content"] = note

    try:
        result = api.post(f"/task/{task_id}", json=payload)
    except Exception as e:
        emit_error(str(e))
        return

    if use_json():
        emit(task_to_dict(result))
    else:
        click.echo(f"Updated: {result['title']}")


@tasks.command("search")
@click.argument("query")
@click.option("-v", "--verbose", is_flag=True, help="Show task details.")
def search_tasks(query, verbose):
    """Search tasks by title."""
    api = get_open_api()
    projects = _get_projects(api)
    if projects is None:
        return
    all_tasks = _get_all_tasks(api, projects)
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
    api = get_open_api()
    projects = _get_projects(api)
    if projects is None:
        return

    task, pid = _resolve_task(api, task_id, None)
    if not task:
        return

    proj = _find_project(projects, project_name)
    if not proj:
        emit_error(f"Project '{project_name}' not found.")
        return

    payload = {"id": task_id, "projectId": proj["id"]}
    try:
        api.post(f"/task/{task_id}", json=payload)
    except Exception as e:
        emit_error(str(e))
        return

    if use_json():
        emit({"status": "moved", "id": task_id, "title": task.get("title"), "project": proj["name"]})
    else:
        click.echo(f"Moved '{task.get('title')}' to '{proj['name']}'")


@tasks.command("due")
@click.option("--days", default=7, type=int, help="Number of days ahead (default: 7).")
@click.option("-v", "--verbose", is_flag=True, help="Show task details.")
def due_tasks(days, verbose):
    """Show tasks due within N days."""
    api = get_open_api()
    projects = _get_projects(api)
    if projects is None:
        return
    all_tasks = _get_all_tasks(api, projects)
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


def _ticktick_due_datetime(date_yyyy_mm_dd: str) -> str:
    # TickTick expects a datetime string; keep it simple and deterministic.
    return f"{date_yyyy_mm_dd}T00:00:00+0000"


def _get_projects(api):
    try:
        return api.get("/project")
    except Exception as e:
        emit_error(str(e))
        return None


def _get_tasks_for_project(api, project_id: str) -> list[dict]:
    try:
        data = api.get(f"/project/{project_id}/data")
    except Exception:
        # If a single project is inaccessible, treat it as empty to keep UX usable.
        return []
    if isinstance(data, dict):
        return data.get("tasks", []) or []
    return []


def _get_all_tasks(api, projects) -> list[dict]:
    tasks = []
    for p in projects:
        pid = p.get("id")
        if not pid:
            continue
        tasks.extend(_get_tasks_for_project(api, pid))
    return tasks


def _find_project(projects, name):
    """Find a project by name (case-insensitive)."""
    name_lower = name.lower()
    for p in projects:
        if p.get("name", "").lower() == name_lower:
            return p
    return None


def _resolve_task(api, task_id: str, project_id: str | None):
    """Return (task, project_id) or (None, None) with an emitted error."""
    if project_id:
        tasks = _get_tasks_for_project(api, project_id)
        for t in tasks:
            if t.get("id") == task_id:
                return t, project_id
        emit_error("Task not found.")
        return None, None

    projects = _get_projects(api)
    if projects is None:
        return None, None
    for p in projects:
        pid = p.get("id")
        if not pid:
            continue
        for t in _get_tasks_for_project(api, pid):
            if t.get("id") == task_id:
                return t, pid

    emit_error("Task not found.")
    return None, None
