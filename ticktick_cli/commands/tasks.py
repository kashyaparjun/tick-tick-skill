"""Task commands for TickTick CLI."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

import click

from ticktick_cli.config import TOKEN_CACHE, load_config
from ticktick_cli.config import get_open_api
from ticktick_cli.datetime_utils import local_date_yyyy_mm_dd
from ticktick_cli.output import (
    PRIORITY_MAP,
    emit,
    emit_error,
    format_task,
    task_to_dict,
    use_json,
)

DUE_MODE_CHOICES = ["strict", "web-today"]
STATUS_CHOICES = ["open", "completed", "all"]


@click.group()
def tasks():
    """Manage tasks."""


@tasks.command("list")
@click.option("-p", "--project", default=None, help="Filter by project name.")
@click.option("-v", "--verbose", is_flag=True, help="Show task details.")
@click.option("--priority", type=click.Choice(["low", "medium", "high"]), help="Filter by priority.")
@click.option("--raw", "raw_output", is_flag=True, help="(JSON only) Include raw TickTick task payload.")
def list_tasks(project, verbose, priority, raw_output):
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

    _emit_tasks(task_list, raw_output=raw_output, verbose=verbose)


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
        if _parse_date_or_emit(due, "due") is None:
            return
        payload["dueDate"] = _ticktick_due_datetime(due)
        payload["isAllDay"] = bool(all_day)

    if note:
        payload["content"] = note

    try:
        result = api.post("/task", json=payload)
    except Exception as exc:
        emit_error(str(exc))
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
    except Exception as exc:
        emit_error(str(exc))
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
    except Exception as exc:
        emit_error(str(exc))
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
        if _parse_date_or_emit(due, "due") is None:
            return
        payload["dueDate"] = _ticktick_due_datetime(due)
        payload["isAllDay"] = True
    if note:
        payload["content"] = note

    try:
        result = api.post(f"/task/{task_id}", json=payload)
    except Exception as exc:
        emit_error(str(exc))
        return

    if use_json():
        emit(task_to_dict(result))
    else:
        click.echo(f"Updated: {result['title']}")


@tasks.command("search")
@click.argument("query")
@click.option("-v", "--verbose", is_flag=True, help="Show task details.")
@click.option("--raw", "raw_output", is_flag=True, help="(JSON only) Include raw TickTick task payload.")
def search_tasks(query, verbose, raw_output):
    """Search tasks by title."""
    api = get_open_api()
    projects = _get_projects(api)
    if projects is None:
        return
    all_tasks = _get_all_tasks(api, projects)
    query_lower = query.lower()
    matches = [t for t in all_tasks if query_lower in t.get("title", "").lower()]

    _emit_tasks(matches, raw_output=raw_output, verbose=verbose, empty_message="No matching tasks.")


@tasks.command("move")
@click.argument("task_id")
@click.argument("project_name")
def move_task(task_id, project_name):
    """Move a task to a different project."""
    api = get_open_api()
    projects = _get_projects(api)
    if projects is None:
        return

    task, _pid = _resolve_task(api, task_id, None)
    if not task:
        return

    proj = _find_project(projects, project_name)
    if not proj:
        emit_error(f"Project '{project_name}' not found.")
        return

    payload = {"id": task_id, "projectId": proj["id"]}
    try:
        api.post(f"/task/{task_id}", json=payload)
    except Exception as exc:
        emit_error(str(exc))
        return

    if use_json():
        emit({"status": "moved", "id": task_id, "title": task.get("title"), "project": proj["name"]})
    else:
        click.echo(f"Moved '{task.get('title')}' to '{proj['name']}'")


@tasks.command("due")
@click.option("--days", default=7, type=int, help="Number of days ahead (default: 7).")
@click.option("-v", "--verbose", is_flag=True, help="Show task details.")
@click.option("--raw", "raw_output", is_flag=True, help="(JSON only) Include raw TickTick task payload.")
def due_tasks(days, verbose, raw_output):
    """Show tasks due within N days (including overdue)."""
    cutoff_date = datetime.now().astimezone().date() + timedelta(days=days)
    due_list = _collect_due_tasks_for_status(
        mode="web-today",
        status_filter="all",
        target_date=cutoff_date,
    )
    if due_list is None:
        return

    _emit_tasks(
        due_list,
        raw_output=raw_output,
        verbose=verbose,
        empty_message=f"No tasks due in the next {days} days.",
    )


@tasks.command("due-on")
@click.option("--date", "date_str", required=True, help="Target date (YYYY-MM-DD).")
@click.option("--mode", type=click.Choice(DUE_MODE_CHOICES), default="strict", show_default=True)
@click.option("--status", "status_filter", type=click.Choice(STATUS_CHOICES), default="all", show_default=True)
@click.option("-v", "--verbose", is_flag=True, help="Show task details.")
@click.option("--raw", "raw_output", is_flag=True, help="(JSON only) Include raw TickTick task payload.")
def due_on_tasks(date_str, mode, status_filter, verbose, raw_output):
    """Show tasks due on a specific day.

    strict mode: due_date == target day
    web-today mode: due_date <= target day (includes overdue)
    """
    target_date = _parse_date_or_emit(date_str, "date")
    if target_date is None:
        return

    due_list = _collect_due_tasks_for_status(
        mode=mode,
        status_filter=status_filter,
        target_date=target_date,
    )
    if due_list is None:
        return

    _emit_tasks(
        due_list,
        raw_output=raw_output,
        verbose=verbose,
        empty_message=f"No tasks due for {target_date.isoformat()}.",
    )


@tasks.command("due-range")
@click.option("--from", "from_str", required=True, help="Start date (YYYY-MM-DD).")
@click.option("--to", "to_str", required=True, help="End date (YYYY-MM-DD).")
@click.option("--mode", type=click.Choice(DUE_MODE_CHOICES), default="strict", show_default=True)
@click.option("--status", "status_filter", type=click.Choice(STATUS_CHOICES), default="all", show_default=True)
@click.option("-v", "--verbose", is_flag=True, help="Show task details.")
@click.option("--raw", "raw_output", is_flag=True, help="(JSON only) Include raw TickTick task payload.")
def due_range_tasks(from_str, to_str, mode, status_filter, verbose, raw_output):
    """Show tasks due in a date range.

    strict mode: from <= due_date <= to
    web-today mode: due_date <= to (from is ignored)
    """
    start_date = _parse_date_or_emit(from_str, "from")
    if start_date is None:
        return
    end_date = _parse_date_or_emit(to_str, "to")
    if end_date is None:
        return
    if start_date > end_date:
        emit_error("Invalid range: --from must be on or before --to.")
        return

    due_list = _collect_due_tasks_for_status(
        mode=mode,
        status_filter=status_filter,
        start_date=start_date,
        end_date=end_date,
    )
    if due_list is None:
        return

    _emit_tasks(
        due_list,
        raw_output=raw_output,
        verbose=verbose,
        empty_message=f"No tasks due for {start_date.isoformat()} to {end_date.isoformat()}.",
    )


@tasks.command("completed")
@click.option("--from", "from_str", required=True, help="Start completion date (YYYY-MM-DD).")
@click.option("--to", "to_str", required=True, help="End completion date (YYYY-MM-DD).")
@click.option("-v", "--verbose", is_flag=True, help="Show task details.")
@click.option("--raw", "raw_output", is_flag=True, help="(JSON only) Include raw TickTick task payload.")
def completed_tasks(from_str, to_str, verbose, raw_output):
    """Show completed tasks by completion date window (private API backend)."""
    start_date = _parse_date_or_emit(from_str, "from")
    if start_date is None:
        return
    end_date = _parse_date_or_emit(to_str, "to")
    if end_date is None:
        return
    if start_date > end_date:
        emit_error("Invalid range: --from must be on or before --to.")
        return

    completed = _get_completed_tasks_from_private_api(start_date, end_date)
    if completed is None:
        return

    _emit_tasks(
        sorted(completed, key=_sort_key),
        raw_output=raw_output,
        verbose=verbose,
        empty_message=f"No completed tasks from {start_date.isoformat()} to {end_date.isoformat()}.",
    )


def _emit_tasks(task_list, raw_output: bool, verbose: bool, empty_message: str = "No tasks found."):
    if use_json():
        if raw_output:
            emit([dict(task_to_dict(task), raw=task) for task in task_list])
        else:
            emit([task_to_dict(task) for task in task_list])
        return

    if not task_list:
        click.echo(empty_message)
        return

    for task in task_list:
        click.echo(format_task(task, verbose))


def _parse_date_or_emit(value: str, label: str) -> date | None:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        emit_error(f"Invalid {label} format. Use YYYY-MM-DD.")
        return None


def _task_status_label(task: dict) -> str:
    return "completed" if task.get("status") == 2 else "open"


def _status_matches(task: dict, status_filter: str) -> bool:
    if status_filter == "all":
        return True
    return _task_status_label(task) == status_filter


def _sort_key(task: dict) -> tuple[str, str, str]:
    local_due = local_date_yyyy_mm_dd(task.get("dueDate")) or "9999-99-99"
    return (local_due, task.get("dueDate", ""), task.get("title", ""))


def _filter_due_tasks(
    tasks: list[dict],
    *,
    mode: str,
    status_filter: str,
    target_date: date | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict]:
    if mode not in DUE_MODE_CHOICES:
        raise ValueError(f"Invalid due mode: {mode}")
    if status_filter not in STATUS_CHOICES:
        raise ValueError(f"Invalid status filter: {status_filter}")

    target_iso = target_date.isoformat() if target_date else None
    start_iso = start_date.isoformat() if start_date else None
    end_iso = end_date.isoformat() if end_date else None

    filtered = []
    for task in tasks:
        due_iso = local_date_yyyy_mm_dd(task.get("dueDate"))
        if not due_iso:
            continue
        if not _status_matches(task, status_filter):
            continue

        if target_iso:
            if mode == "strict":
                include = due_iso == target_iso
            else:
                include = due_iso <= target_iso
        elif start_iso and end_iso:
            if mode == "strict":
                include = start_iso <= due_iso <= end_iso
            else:
                include = due_iso <= end_iso
        else:
            raise ValueError("Either target_date or both start_date and end_date are required.")

        if include:
            filtered.append(task)

    return sorted(filtered, key=_sort_key)


def _collect_due_tasks_for_status(
    *,
    mode: str,
    status_filter: str,
    target_date: date | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict] | None:
    open_tasks: list[dict] = []
    if status_filter in ("open", "all"):
        api = get_open_api()
        projects = _get_projects(api)
        if projects is None:
            return None
        all_open = _get_all_tasks(api, projects)
        open_tasks = _filter_due_tasks(
            all_open,
            mode=mode,
            status_filter="open",
            target_date=target_date,
            start_date=start_date,
            end_date=end_date,
        )

    completed_tasks: list[dict] = []
    if status_filter in ("completed", "all"):
        private_start, private_end = _due_query_window(target_date=target_date, start_date=start_date, end_date=end_date)
        completed_raw = _get_completed_tasks_from_private_api(private_start, private_end)
        if completed_raw is None:
            if status_filter == "completed":
                return None
        else:
            completed_tasks = _filter_due_tasks(
                completed_raw,
                mode=mode,
                status_filter="completed",
                target_date=target_date,
                start_date=start_date,
                end_date=end_date,
            )

    merged = _merge_by_id(open_tasks, completed_tasks)
    return sorted(merged, key=_sort_key)


def _due_query_window(
    *,
    target_date: date | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> tuple[date, date]:
    if target_date is not None:
        return target_date, target_date
    if start_date is not None and end_date is not None:
        return start_date, end_date
    raise ValueError("Either target_date or both start_date and end_date are required.")


def _merge_by_id(first: list[dict], second: list[dict]) -> list[dict]:
    merged: dict[str, dict] = {}
    for task in first:
        task_id = task.get("id")
        if task_id:
            merged[task_id] = task
    for task in second:
        task_id = task.get("id")
        if task_id:
            merged[task_id] = task
    return list(merged.values())


def _private_client_or_error():
    config = load_config()
    required = ["username", "password", "client_id", "client_secret", "redirect_uri"]
    missing = [key for key in required if not config.get(key)]
    if missing:
        emit_error("completed_history_unavailable: missing credentials in config.json; run tt auth signin")
        return None
    if not TOKEN_CACHE.exists():
        emit_error("completed_history_unavailable: missing OAuth token cache; run tt auth signin")
        return None

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
    except Exception as exc:
        emit_error(f"completed_history_unavailable: private API login failed: {exc}")
        return None


def _get_completed_tasks_from_private_api(start_date: date, end_date: date) -> list[dict] | None:
    client = _private_client_or_error()
    if client is None:
        return None
    try:
        start_dt = datetime.combine(start_date, time.min)
        end_dt = datetime.combine(end_date, time.max.replace(microsecond=0))
        completed = client.task.get_completed(start_dt, end_dt, full=True)
        return completed if isinstance(completed, list) else []
    except Exception as exc:
        emit_error(f"completed_history_unavailable: failed fetching completed tasks: {exc}")
        return None


def _ticktick_due_datetime(date_yyyy_mm_dd: str) -> str:
    # TickTick expects a datetime string; keep it simple and deterministic.
    return f"{date_yyyy_mm_dd}T00:00:00+00:00"


def _get_projects(api):
    try:
        return api.get("/project")
    except Exception as exc:
        emit_error(str(exc))
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
    for project in projects:
        pid = project.get("id")
        if not pid:
            continue
        tasks.extend(_get_tasks_for_project(api, pid))
    return tasks


def _find_project(projects, name):
    """Find a project by name (case-insensitive)."""
    name_lower = name.lower()
    for project in projects:
        if project.get("name", "").lower() == name_lower:
            return project
    return None


def _resolve_task(api, task_id: str, project_id: str | None):
    """Return (task, project_id) or (None, None) with an emitted error."""
    if project_id:
        tasks = _get_tasks_for_project(api, project_id)
        for task in tasks:
            if task.get("id") == task_id:
                return task, project_id
        emit_error("Task not found.")
        return None, None

    projects = _get_projects(api)
    if projects is None:
        return None, None
    for project in projects:
        pid = project.get("id")
        if not pid:
            continue
        for task in _get_tasks_for_project(api, pid):
            if task.get("id") == task_id:
                return task, pid

    emit_error("Task not found.")
    return None, None
