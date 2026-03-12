# TickTick CLI Skill

Manage TickTick tasks and projects via the `tt` command. Always use `--json` for structured output.

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

# Tasks due within N days (default 7)
tt --json tasks due
tt --json tasks due --days 3
```

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
  "project_id": "string",
  "content": "string | null",
  "items": [{"title": "string", "done": true}]
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
- The TickTick Open API cannot see tasks in the default Inbox. Tasks must be in a named project.
