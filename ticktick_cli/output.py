"""Shared output helpers for human and JSON formatting."""

import json
import sys

import click

from ticktick_cli.datetime_utils import local_date_yyyy_mm_dd

PRIORITY_MAP = {"none": 0, "low": 1, "medium": 3, "high": 5}
PRIORITY_LABELS = {0: "none", 1: "low", 3: "medium", 5: "high"}


def use_json() -> bool:
    ctx = click.get_current_context(silent=True)
    return ctx and ctx.find_root().params.get("json_output", False)


def emit(data):
    """Output data as JSON and exit. Used for structured output mode."""
    click.echo(json.dumps(data, indent=2, default=str))


def emit_error(msg: str):
    """Output an error — JSON object or plain text depending on mode."""
    if use_json():
        emit({"error": msg})
    else:
        click.echo(msg, err=True)


def task_to_dict(t: dict) -> dict:
    return {
        "id": t.get("id"),
        "title": t.get("title"),
        "status": "completed" if t.get("status") == 2 else "open",
        "priority": PRIORITY_LABELS.get(t.get("priority", 0), "none"),
        "due_date": local_date_yyyy_mm_dd(t.get("dueDate")),
        "due_datetime_raw": t.get("dueDate") or None,
        "project_id": t.get("projectId"),
        "content": t.get("content") or None,
        "items": [
            {"title": i.get("title"), "done": i.get("status") == 2}
            for i in t.get("items", [])
        ] or None,
    }


def project_to_dict(p: dict) -> dict:
    return {
        "id": p.get("id"),
        "name": p.get("name"),
        "kind": p.get("kind", "TASK"),
        "color": p.get("color"),
    }


def tag_to_dict(t: dict) -> dict:
    return {
        "label": t.get("label", t.get("name")),
        "color": t.get("color"),
        "parent": t.get("parent"),
    }


def format_task(task, verbose=False):
    """Format a task for human display."""
    priority = PRIORITY_LABELS.get(task.get("priority", 0), "?")
    title = task.get("title", "Untitled")
    project_id = task.get("projectId", "")
    status_icon = "x" if task.get("status", 0) == 2 else " "

    line = f"  [{status_icon}] {title}"
    if priority != "none":
        line += f"  [{priority}]"

    due = task.get("dueDate")
    if due:
        line += f"  (due: {due[:10]})"

    if verbose:
        line += f"\n      ID: {task.get('id', 'N/A')}"
        line += f"  Project: {project_id}"
        if task.get("content"):
            line += f"\n      Note: {task['content']}"
        items = task.get("items", [])
        for item in items:
            sub_icon = "x" if item.get("status", 0) == 2 else " "
            line += f"\n      [{sub_icon}] {item.get('title', '')}"

    return line


def format_project(proj, verbose=False):
    """Format a project for human display."""
    name = proj.get("name", "Untitled")
    kind = proj.get("kind", "TASK")
    line = f"  {name}"
    if kind != "TASK":
        line += f"  ({kind})"
    if verbose:
        line += f"\n      ID: {proj.get('id', 'N/A')}"
        color = proj.get("color")
        if color:
            line += f"  Color: {color}"
    return line
