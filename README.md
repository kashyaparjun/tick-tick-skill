# tick-tick-skill

A CLI tool for [TickTick](https://ticktick.com) that doubles as an LLM skill. Manage tasks and projects from the terminal — or let an AI agent do it for you via `--json` mode.

Uses the [TickTick Open API v1](https://developer.ticktick.com/api) directly — no third-party wrappers.

## Install

```bash
# Option 1: pipx (recommended — installs globally)
pipx install git+https://github.com/kashyaparjun/tick-tick-skill.git

# Option 2: from source
git clone https://github.com/kashyaparjun/tick-tick-skill.git
cd tick-tick-skill
pip install .
```

This installs the `tt` command.

## Authentication

TickTick uses OAuth2. One-time setup:

1. Go to [TickTick Developer Portal](https://developer.ticktick.com/manage) and register an app
2. Set the redirect URI to `http://localhost:8080`
3. Run:

```bash
tt auth signin
```

This will:
- Prompt for your OAuth client ID and client secret
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

## Important: Inbox tasks are invisible to the API

> **The TickTick Open API cannot see tasks in the default Inbox.** The `GET /project` endpoint does not return the Inbox, and no v1 endpoint can retrieve tasks that live there. If all your tasks are in the Inbox, the CLI will return empty results.

**Workaround:** Create a project (e.g. "00 Inbox") and move your tasks into it. Then hide the built-in Inbox through TickTick's settings so new tasks go to your project instead. Once tasks are in a named project, the API — and this CLI — can see them.

This is a TickTick API limitation, not a bug in this tool.

## Usage

### Tasks

The TickTick Open API requires both a task ID and project ID for single-task operations. Use `tt tasks list -v` or `tt --json tasks list` to get both IDs.

```bash
# List all tasks
tt tasks list
tt tasks list -p "Work" --priority high
tt tasks list -v                          # verbose (shows IDs, notes, subtasks)

# Create a task
tt tasks add "Buy groceries"
tt tasks add "Ship feature" -p "Work" --priority high --due 2026-03-15 --note "See spec doc"

# Complete, update, delete (require task_id and project_id)
tt tasks done <task_id> <project_id>
tt tasks update <task_id> <project_id> --title "New title" --priority medium
tt tasks delete <task_id> <project_id>
tt tasks delete <task_id> <project_id> -y   # skip confirmation

# Search and filter
tt tasks search "groceries"
tt tasks due                              # due within 7 days
tt tasks due --days 3                     # due within 3 days
```

### Projects

```bash
tt projects list
tt projects add "Side Project"
tt projects add "Design" --color "#ff6600"
tt projects tasks "Work"                  # list tasks in a project
tt projects delete "Old Project"
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
  tt --json tasks done TASK_ID PROJECT_ID
  tt --json tasks delete TASK_ID PROJECT_ID -y
  tt --json tasks update TASK_ID PROJECT_ID [--title TEXT] [--priority LEVEL] [--due YYYY-MM-DD]
  tt --json tasks search "QUERY"
  tt --json tasks due [--days N]
  tt --json projects list
  tt --json projects add "NAME"
  tt --json projects delete "NAME" -y
  tt --json projects tasks "NAME"
```

## Config location

All config and tokens are stored in `~/.config/ticktick-cli/`:

| File | Contents |
|------|----------|
| `config.json` | OAuth app credentials |
| `.token-oauth` | Cached OAuth token (expires ~6 months) |

## License

MIT
