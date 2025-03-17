# Work Log CLI

A command-line time tracking tool for managing work across multiple projects.

## Features

- Create, update, and delete projects
- Track time spent on tasks within projects
- Generate daily and weekly reports
- Support for hourly billing rates
- Beautiful CLI interface with colorful output

## Requirements

- uv (`brew install uv` for Mac OS)

### Quick Setup

Install dependencies:

```bash
uv sync
```

### Setup alias (Recommended)

Create an alias:

```bash
echo "alias wl=\"uv run --directory $(pwd) main.py \$@\"" >> ~/.zshrc
```

Now you can use the `wl` command from anywhere!

## Usage

### Project Management

```bash
# List all projects
wl projects

# Add a new project
wl project-add "Project Name" [--hourly] [--rate RATE]

# Update a project
wl project-update PROJECT_ID [--name "New Name"] [--hourly/--no-hourly] [--rate RATE]

# Delete a project
wl project-delete PROJECT_ID [--force]
```

### Time Tracking

```bash
# Start working on a task (using project name or ID)
wl start "Project Name" "Task description"

# Check current work status
wl status

# Stop the current task
wl stop
```

### Reporting

```bash
# Show today's report
wl today

# Show yesterday's report
wl yesterday

# Show report for a specific day
wl day 2023-05-15

# Show weekly report (defaults to current week)
wl week [YYYY-MM-DD]
```

## Data Storage

All data is stored in a SQLite database located at `~/.work-log/work-log.db`.

## Development

### Running Tests

The project includes a comprehensive test suite that covers the core functionality:

```bash
# Run all tests
pytest

# Run tests with verbose output
pytest -v

# Run a specific test file
pytest tests/test_workflow.py
```

### Manual Testing

After making changes, you can test using the wrapper script:

```bash
# Test a specific command
uv run main.py projects

# Debug mode with detailed output
UV_LOG=debug uv run main.py status
```

The tests cover:
- Basic database operations (CRUD) for projects and work entries
- Time tracking functionality
- Report generation
- CLI commands and output

## License

MIT
