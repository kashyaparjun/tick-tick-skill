# TickTick CLI Skill

Manage TickTick tasks and projects via the `tt` command. Always use `--json` for structured output.

## Install

```bash
pipx install git+https://github.com/kashyaparjun/tick-tick-skill.git
```

One-time auth setup:

1. Register an app at [TickTick Developer Portal](https://developer.ticktick.com/manage), set redirect URI to `http://localhost:8080`.
2. Run `tt auth signin` and follow the prompts.

## Prerequisites

- `tt` must be installed and on PATH
- User must have run `tt auth signin` to authenticate

## Commands

### Tasks

```bash
# List all tasks (or filter by project/priority)
tt --json tasks list
tt --json tasks list -p "PROJECT_NAME"
tt --json tasks list --priority high  # low | medium | high
tt --json tasks list --raw            # include raw TickTick payloads

# Create a task
tt --json tasks add "TITLE"
tt --json tasks add "TITLE" -p "PROJECT_NAME" --priority medium --due 2026-03-15 --note "details"

# Complete a task
tt --json tasks done TASK_ID PROJECT_ID

# Update a task
tt --json tasks update TASK_ID PROJECT_ID --title "New title"
tt --json tasks update TASK_ID PROJECT_ID --priority high --due 2026-04-01

# Delete a task (use -y to skip confirmation)
tt --json tasks delete TASK_ID PROJECT_ID -y

# Search tasks by title
tt --json tasks search "QUERY"
tt --json tasks search "QUERY" --raw

# Tasks due within N days (includes overdue, default 7)
tt --json tasks due
tt --json tasks due --days 3
tt --json tasks due --days 3 --raw

# Tasks due on a specific day
tt --json tasks due-on --date 2026-03-15
tt --json tasks due-on --date 2026-03-15 --mode strict --status all
tt --json tasks due-on --date 2026-03-15 --mode web-today --status open

# Tasks due in a date range
tt --json tasks due-range --from 2026-03-09 --to 2026-03-15
tt --json tasks due-range --from 2026-03-09 --to 2026-03-15 --mode strict --status all
tt --json tasks due-range --from 2026-03-09 --to 2026-03-15 --mode web-today --status open

# Completed tasks by completion-date window (private API backend)
tt --json tasks completed --from 2026-03-15 --to 2026-03-15
tt --json tasks completed --from 2026-03-09 --to 2026-03-15 --raw
```

Due mode semantics:
- `strict`: exact due date matching
- `web-today`: include overdue (`<= target day`); for `due-range`, this is `<= --to` (the lower bound is ignored)

Status filter values:
- `open` (default)
- `completed`
- `all`

### Projects

```bash
# List all projects
tt --json projects list

# Create a project
tt --json projects add "NAME"

# List tasks in a project
tt --json projects tasks "NAME"

# Delete a project and all its tasks
tt --json projects delete "NAME" -y
```

## Output format

All `--json` responses return either a JSON array or object.

Task object:
```json
{
  "id": "string",
  "title": "string",
  "status": "open | completed",
  "priority": "none | low | medium | high",
  "due_date": "YYYY-MM-DD | null",
  "due_datetime_raw": "ISO-8601 string | null",
  "project_id": "string",
  "content": "string | null",
  "items": [{"title": "string", "done": true}]
}
```

When `--raw` is used (JSON mode only), each task object also includes:
```json
{
  "raw": {"...": "Original TickTick task payload"}
}
```

Project object:
```json
{
  "id": "string",
  "name": "string",
  "kind": "TASK",
  "color": "string | null"
}
```

Errors:
```json
{"error": "description"}
```

## Notes

- Task operations like `done`, `update`, and `delete` require both `TASK_ID` and `PROJECT_ID`. Get these from `tt --json tasks list`.
- Priority values: `none` (0), `low` (1), `medium` (3), `high` (5).
- Due dates use `YYYY-MM-DD` format.
- Local date normalization is used for due filtering (`dueDate` is converted to system timezone before date comparisons).
- Completed-task history comes from TickTick's private API backend; if unavailable, the CLI returns:
  `{"error":"completed_history_unavailable: ..."}`
- The TickTick Open API cannot see tasks in the default Inbox. Tasks must be in a named project.
