# tick-tick-skill

A CLI tool for [TickTick](https://ticktick.com) that doubles as an LLM skill. Manage tasks and projects from the terminal, or let an AI agent do it via `--json` mode.

Uses the [TickTick Open API v1](https://developer.ticktick.com/api) directly.

## Install

```bash
# Option 1: pipx (recommended)
pipx install git+https://github.com/kashyaparjun/tick-tick-skill.git

# Option 2: from source
git clone https://github.com/kashyaparjun/tick-tick-skill.git
cd tick-tick-skill
pip install .
```

This installs the `tt` command.

## Authentication

TickTick uses OAuth2. One-time setup:

1. Go to [TickTick Developer Portal](https://developer.ticktick.com/manage) and register an app.
2. Set redirect URI to `http://localhost:8080`.
3. Run:

```bash
tt auth signin
```

Check status:

```bash
tt auth status
```

Sign out:

```bash
tt auth signout
```

## Important: Inbox tasks are invisible to the API

> The TickTick Open API cannot see tasks in the default Inbox.

Workaround: create a named project (for example `00 Inbox`) and move tasks there.

## Usage

### Tasks

Single-task operations require both `task_id` and `project_id`. Use `tt --json tasks list` (or `tt tasks list -v`) to retrieve both.

```bash
# List tasks
tt tasks list
tt tasks list -p "Work" --priority high
tt tasks list -v
tt --json tasks list --raw

# Create
tt tasks add "Buy groceries"
tt tasks add "Ship feature" -p "Work" --priority high --due 2026-03-15 --note "See spec"

# Complete / update / delete
tt tasks done <task_id> <project_id>
tt tasks update <task_id> <project_id> --title "New title" --priority medium
tt tasks delete <task_id> <project_id>
tt tasks delete <task_id> <project_id> -y

# Search
tt tasks search "groceries"
tt --json tasks search "groceries" --raw

# Due window (includes overdue up to cutoff)
tt tasks due
tt tasks due --days 3

# Due for a specific day
tt tasks due-on --date 2026-03-15
tt tasks due-on --date 2026-03-15 --mode strict --status all
tt tasks due-on --date 2026-03-15 --mode web-today --status open

# Due in a range
tt tasks due-range --from 2026-03-09 --to 2026-03-15
tt tasks due-range --from 2026-03-09 --to 2026-03-15 --mode strict --status all
tt tasks due-range --from 2026-03-09 --to 2026-03-15 --mode web-today --status open
```

Mode semantics:
- `strict`: exact matching by normalized local `due_date`
- `web-today`: include overdue (`<= target`); for `due-range`, this means `<= --to` and ignores `--from`

Status filter:
- `open`
- `completed`
- `all` (default)

### Projects

```bash
tt projects list
tt projects add "Side Project"
tt projects add "Design" --color "#ff6600"
tt projects tasks "Work"
tt projects delete "Old Project"
```

## JSON mode (for LLMs)

Use `--json` before any command.

```bash
tt --json tasks due-on --date 2026-03-15 --mode strict --status all --raw
```

Example task object:

```json
{
  "id": "6abc123def",
  "title": "Buy groceries",
  "status": "open",
  "priority": "high",
  "due_date": "2026-03-15",
  "due_datetime_raw": "2026-03-14T23:00:00.000+0000",
  "project_id": "5def456abc",
  "content": "Milk, eggs, bread",
  "items": null,
  "raw": {
    "id": "6abc123def",
    "dueDate": "2026-03-14T23:00:00.000+0000",
    "timeZone": "Europe/Berlin"
  }
}
```

Notes:
- In JSON mode, `--raw` appends the original TickTick payload per task.
- `due_date` is derived from `dueDate` after converting to system local timezone.
- Errors return `{"error": "..."}`.

### LLM skill usage

The CLI is designed for agent/tool use. Recommended contract:

```text
Always use `tt --json`.
Use `tasks due-on` for exact day queries.
Use `tasks due-range` for historical windows.
Use `--mode web-today` only when you intentionally want overdue-inclusive behavior.
```

## Config location

Files are stored in `~/.config/ticktick-cli/`:

| File | Contents |
|------|----------|
| `config.json` | OAuth app credentials |
| `.token-oauth` | Cached OAuth token |

## License

MIT
