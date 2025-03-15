#!/usr/bin/env python3
import sys
from app.cli import app, console

def main():
    """
    Entry point for the CLI application.
    Shows help when no arguments are provided.
    """
    if len(sys.argv) == 1:
        # No arguments provided, show help
        console.print("\n[bold]Work Log[/bold] - Track your work across projects\n")
        console.print("To see available commands, run: [cyan]work-log --help[/cyan]")
        console.print("For help on a specific command, run: [cyan]work-log COMMAND --help[/cyan]")
        console.print("\nCommon commands:")
        console.print("  [green]projects[/green]    List all projects")
        console.print("  [green]start[/green]       Start working on a task")
        console.print("  [green]status[/green]      Check current work status")
        console.print("  [green]stop[/green]        Stop the current task")
        console.print("  [green]today[/green]       Show today's work report")
        sys.exit(0)
    
    # Pass control to Typer app
    app()

if __name__ == "__main__":
    main()
