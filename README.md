# tick-tick-skill

A CLI tool for [TickTick](https://ticktick.com) that doubles as an LLM skill. Manage tasks, projects, and tags from the terminal — or let an AI agent do it for you via `--json` mode.

Built on [ticktick-py](https://github.com/lazeroffmichael/ticktick-py).

## Install

```bash
git clone https://github.com/kashyaparjun/tick-tick-skill.git
cd tick-tick-skill
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

This installs the `tt` command.

## Authentication

TickTick requires OAuth2 credentials. One-time setup:

1. Go to [TickTick Developer Portal](https://developer.ticktick.com/manage) and register an app
2. Set the redirect URI to `http://localhost:8080`
3. Run:

```bash
tt auth signin
```

This will:
- Prompt for your OAuth client ID, client secret, and TickTick account credentials
- Open your browser for authorization
- Automatically capture the OAuth redirect (no manual URL pasting)
- Cache the token at `~/.config/ticktick-cli/`

Check your auth status anytime:

```bash
tt auth status
```

Log out (clears tokens):

```bash
tt auth signout
```

## Usage

### Tasks

```bash
# List all tasks
tt tasks list
tt tasks list -p "Work" --priority high
tt tasks list -v                          # verbose (shows IDs, notes, subtasks)

# Create a task
tt tasks add "Buy groceries"
tt tasks add "Ship feature" -p "Work" --priority high --due 2026-03-15 --note "See spec doc"

# Complete, update, delete
tt tasks done <task_id>
tt tasks update <task_id> --title "New title" --priority medium
tt tasks delete <task_id>
tt tasks delete <task_id> -y              # skip confirmation

# Search and filter
tt tasks search "groceries"
tt tasks due                              # due within 7 days
tt tasks due --days 3                     # due within 3 days

# Move to another project
tt tasks move <task_id> "Personal"
```

### Projects

```bash
tt projects list
tt projects add "Side Project"
tt projects add "Design" --color "#ff6600"
tt projects tasks "Work"                  # list tasks in a project
tt projects delete "Old Project"
```

### Tags

```bash
tt tags list
tt tags add "urgent"
tt tags add "frontend" --color "#00ff00" --parent "engineering"
tt tags rename "urgent" "critical"
tt tags delete "old-tag"
```

## JSON mode (for LLMs)

Add `--json` before any command to get structured output. This is what makes it usable as an LLM skill — any agent can shell out to `tt` and parse the results.

```bash
tt --json tasks list
```

```json
[
  {
    "id": "6abc123def",
    "title": "Buy groceries",
    "status": "open",
    "priority": "high",
    "due_date": "2026-03-15",
    "project_id": "5def456abc",
    "content": "Milk, eggs, bread",
    "items": null
  }
]
```

```bash
tt --json tasks add "Review PR" -p "Work" --priority medium
```

```json
{
  "id": "7xyz789",
  "title": "Review PR",
  "status": "open",
  "priority": "medium",
  "due_date": null,
  "project_id": "5def456abc",
  "content": null,
  "items": null
}
```

In JSON mode:
- Interactive confirmations are skipped automatically
- Errors return `{"error": "..."}`
- Empty results return `[]`

### Using as an LLM skill

Any LLM that can execute shell commands can use this as a tool. Example system prompt snippet:

```
You have access to TickTick via the `tt` CLI. Always use `tt --json` for structured output.

Available commands:
  tt --json tasks list [-p PROJECT] [--priority low|medium|high]
  tt --json tasks add "TITLE" [-p PROJECT] [--priority LEVEL] [--due YYYY-MM-DD] [--note TEXT]
  tt --json tasks done TASK_ID
  tt --json tasks delete TASK_ID -y
  tt --json tasks update TASK_ID [--title TEXT] [--priority LEVEL] [--due YYYY-MM-DD]
  tt --json tasks search "QUERY"
  tt --json tasks due [--days N]
  tt --json tasks move TASK_ID "PROJECT"
  tt --json projects list
  tt --json projects add "NAME"
  tt --json projects delete "NAME" -y
  tt --json projects tasks "NAME"
  tt --json tags list
  tt --json tags add "LABEL"
  tt --json tags delete "LABEL" -y
  tt --json tags rename "OLD" "NEW"
```

## Config location

All config and tokens are stored in `~/.config/ticktick-cli/`:

| File | Contents |
|------|----------|
| `config.json` | OAuth app credentials and account info |
| `.token-oauth` | Cached OAuth token |

## License

MIT
