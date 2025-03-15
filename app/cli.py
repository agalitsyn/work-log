from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional

import typer
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.table import Table
from rich.text import Text

from .db import Database
from .models import Project, WorkEntry

app = typer.Typer(
    help="Work Log CLI - Track your work across projects", no_args_is_help=True
)
console = Console()

# Initialize database
db = Database()


@app.callback(invoke_without_command=True)
def callback(ctx: typer.Context):
    """
    Work Log CLI - Track your work across projects.
    """
    # This will be called for invalid subcommand names and other errors
    if ctx.invoked_subcommand is None and ctx.args:
        # Only show error if there were arguments (not when no args are provided)
        console.print("[red]Error:[/red] Unknown command or invalid arguments")
        console.print("Run [cyan]work-log --help[/cyan] to see available commands")
        raise typer.Exit(code=1)


# Project commands
@app.command("projects")
def list_projects():
    """List all projects"""
    projects = db.get_all_projects()

    if not projects:
        console.print(
            "[yellow]No projects found. Create one with 'work-log project add <name>'[/yellow]"
        )
        return

    table = Table(title="Projects", box=box.ROUNDED)
    table.add_column("ID", style="dim")
    table.add_column("Name", style="green")
    table.add_column("Billing", style="cyan")
    table.add_column("Rate", style="yellow")

    for project in projects:
        billing = "Hourly" if project.is_billed_hourly else "Fixed"
        rate = f"${project.hour_rate}/h" if project.hour_rate else "N/A"
        table.add_row(str(project.id), project.name, billing, rate)

    console.print(table)


@app.command("project-add")
def add_project(
    name: str = typer.Argument(..., help="Project name"),
    hourly: bool = typer.Option(False, "--hourly", "-h", help="Bill hourly"),
    rate: Optional[float] = typer.Option(None, "--rate", "-r", help="Hourly rate"),
):
    """Add a new project"""
    existing = db.get_project_by_name(name)
    if existing:
        console.print(f"[red]Project '{name}' already exists[/red]")
        return

    decimal_rate = Decimal(str(rate)) if rate is not None else None
    project = Project(name=name, is_billed_hourly=hourly, hour_rate=decimal_rate)
    project_id = db.create_project(project)

    console.print(f"[green]Project '{name}' added with ID {project_id}[/green]")


@app.command("project-update")
def update_project(
    id: int = typer.Argument(..., help="Project ID"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="New project name"),
    hourly: Optional[bool] = typer.Option(
        None, "--hourly/--no-hourly", help="Bill hourly"
    ),
    rate: Optional[float] = typer.Option(None, "--rate", "-r", help="Hourly rate"),
):
    """Update an existing project"""
    project = db.get_project(id)
    if not project:
        console.print(f"[red]Project with ID {id} not found[/red]")
        return

    if name:
        project.name = name
    if hourly is not None:
        project.is_billed_hourly = hourly
    if rate is not None:
        project.hour_rate = Decimal(str(rate))

    if db.update_project(project):
        console.print(f"[green]Project '{project.name}' updated[/green]")
    else:
        console.print("[red]Failed to update project[/red]")


@app.command("project-delete")
def delete_project(
    id: int = typer.Argument(..., help="Project ID"),
    force: bool = typer.Option(
        False, "--force", "-f", help="Force deletion without confirmation"
    ),
):
    """Delete a project"""
    project = db.get_project(id)
    if not project:
        console.print(f"[red]Project with ID {id} not found[/red]")
        return

    if not force:
        confirm = Confirm.ask(
            f"Are you sure you want to delete project '{project.name}'?"
        )
        if not confirm:
            console.print("Operation cancelled")
            return

    if db.delete_project(id):
        console.print(f"[green]Project '{project.name}' deleted[/green]")
    else:
        console.print("[red]Failed to delete project[/red]")


# Work entry commands
@app.command("start")
def start_work(
    project: str = typer.Argument(..., help="Project name or ID"),
    description: str = typer.Argument(..., help="Work description"),
):
    """Start working on a task"""
    # Check for active work
    active_entry = db.get_active_work_entry()
    if active_entry:
        active_entry_project = db.get_project(active_entry.project_id)
        console.print(
            f"[yellow]You already have an active task: {active_entry.description} on {active_entry_project.name}[/yellow]"
        )
        stop_current = Confirm.ask(
            "Would you like to stop the current task and start a new one?"
        )
        if stop_current:
            active_entry.end_time = datetime.now()
            db.update_work_entry(active_entry)
            console.print(
                f"[green]Stopped work on '{active_entry.description}'[/green]"
            )
        else:
            console.print("Operation cancelled")
            return

    # Find the project
    target_project = None
    try:
        # Check if the input is a project ID
        project_id = int(project)
        target_project = db.get_project(project_id)
    except ValueError:
        # If not, treat it as a project name
        target_project = db.get_project_by_name(project)

    if not target_project:
        console.print(f"[red]Project '{project}' not found[/red]")
        return

    # Create the work entry
    entry = WorkEntry(
        project_id=target_project.id,
        description=description,
        start_time=datetime.now(),
    )
    entry_id = db.create_work_entry(entry)

    console.print(
        f"[green]Started work on '{description}' for project '{target_project.name}'[/green]"
    )


@app.command("stop")
def stop_work():
    """Stop the current active work"""
    active_entry = db.get_active_work_entry()
    if not active_entry:
        console.print("[yellow]No active work to stop[/yellow]")
        return

    active_entry.end_time = datetime.now()
    db.update_work_entry(active_entry)

    active_project = db.get_project(active_entry.project_id)
    duration = active_entry.end_time - active_entry.start_time
    hours = duration.total_seconds() / 3600

    console.print(
        f"[green]Stopped work on '{active_entry.description}' for project '{active_project.name}'[/green]"
    )
    console.print(f"[cyan]Duration: {hours:.2f} hours[/cyan]")


@app.command("status")
def status():
    """Show current work status"""
    active_entry = db.get_active_work_entry()
    if not active_entry:
        console.print("[yellow]No active work[/yellow]")
        return

    active_project = db.get_project(active_entry.project_id)
    duration = datetime.now() - active_entry.start_time
    hours = duration.total_seconds() / 3600

    text = Text()
    text.append("Currently working on: ", style="bold")
    text.append(active_entry.description, style="green bold")
    text.append("\nProject: ", style="bold")
    text.append(active_project.name, style="cyan")
    text.append("\nStarted at: ", style="bold")
    text.append(active_entry.start_time.strftime("%H:%M:%S"), style="yellow")
    text.append("\nElapsed time: ", style="bold")
    text.append(f"{hours:.2f} hours", style="red")

    panel = Panel(text, title="Work Status", box=box.ROUNDED)
    console.print(panel)


# Reporting commands
@app.command("today")
def today_report():
    """Show today's work report"""
    today = date.today()
    _show_day_report(today)


@app.command("yesterday")
def yesterday_report():
    """Show yesterday's work report"""
    yesterday = date.today() - timedelta(days=1)
    _show_day_report(yesterday)


@app.command("day")
def day_report(day: str = typer.Argument(..., help="Day in YYYY-MM-DD format")):
    """Show work report for a specific day"""
    try:
        report_date = datetime.strptime(day, "%Y-%m-%d").date()
        _show_day_report(report_date)
    except ValueError:
        console.print("[red]Invalid date format. Use YYYY-MM-DD[/red]")


@app.command("week")
def week_report(
    day: Optional[str] = typer.Argument(
        None, help="Day in the week in YYYY-MM-DD format (defaults to today)"
    ),
):
    """Show work report for the week containing the specified day"""
    if day:
        try:
            report_date = datetime.strptime(day, "%Y-%m-%d").date()
        except ValueError:
            console.print("[red]Invalid date format. Use YYYY-MM-DD[/red]")
            return
    else:
        report_date = date.today()

    _show_week_report(report_date)


def _show_day_report(day: date):
    """Helper function to show daily report"""
    entries = db.get_entries_for_day(day)

    if not entries:
        console.print(
            f"[yellow]No work entries for {day.strftime('%Y-%m-%d')}[/yellow]"
        )
        return

    # Group entries by project
    projects_dict = {}
    entries_by_project = defaultdict(list)

    for entry, project in entries:
        projects_dict[project.id] = project
        entries_by_project[project.id].append(entry)

    # Calculate totals
    total_hours = 0
    project_hours = {}

    for project_id, project_entries in entries_by_project.items():
        project_total = 0
        for entry in project_entries:
            if entry.duration_hours:
                project_total += entry.duration_hours

        project_hours[project_id] = project_total
        total_hours += project_total

    # Display report
    console.print(f"[bold]Work Report for {day.strftime('%A, %B %d, %Y')}[/bold]")

    # Create table per project
    for project_id, project_entries in entries_by_project.items():
        project = projects_dict[project_id]

        table = Table(show_header=True, header_style="bold", box=box.SIMPLE)
        table.add_column("Task")
        table.add_column("Start", style="cyan")
        table.add_column("End", style="cyan")
        table.add_column("Hours", style="green", justify="right")

        for entry in project_entries:
            start_time = (
                entry.start_time.strftime("%H:%M") if entry.start_time else "N/A"
            )
            end_time = (
                entry.end_time.strftime("%H:%M") if entry.end_time else "In progress"
            )
            duration = f"{entry.duration_hours:.2f}" if entry.duration_hours else "N/A"

            table.add_row(entry.description, start_time, end_time, duration)

        # Add the total row
        table.add_row("TOTAL", "", "", f"{project_hours[project_id]:.2f}", style="bold")

        # Calculate billing if applicable
        billing_info = ""
        if project.is_billed_hourly and project.hour_rate:
            # Convert float to Decimal for multiplication with Decimal
            amount = Decimal(str(project_hours[project_id])) * project.hour_rate
            billing_info = f" (${amount:.2f} at ${project.hour_rate}/hour)"

        console.print(
            f"[bold]{project.name}[/bold] - {project_hours[project_id]:.2f} hours{billing_info}"
        )
        console.print(table)

    console.print(f"[bold]Total Hours: {total_hours:.2f}[/bold]")


def _show_week_report(day_in_week: date):
    """Helper function to show weekly report"""
    # Find the start and end of the week
    start_of_week = day_in_week - timedelta(days=day_in_week.weekday())
    end_of_week = start_of_week + timedelta(days=6)

    entries = db.get_entries_for_week(day_in_week)

    if not entries:
        console.print(
            f"[yellow]No work entries for week of {start_of_week.strftime('%Y-%m-%d')} to {end_of_week.strftime('%Y-%m-%d')}[/yellow]"
        )
        return

    # Group entries by project and day
    projects_dict = {}
    entries_by_project = defaultdict(lambda: defaultdict(list))
    days_in_week = [(start_of_week + timedelta(days=i)) for i in range(7)]

    for entry, project in entries:
        projects_dict[project.id] = project
        entry_date = entry.start_time.date()
        entries_by_project[project.id][entry_date].append(entry)

    # Calculate totals
    total_hours = 0
    project_hours = defaultdict(float)
    day_hours = defaultdict(float)

    for project_id, date_entries in entries_by_project.items():
        for day_date, day_entries in date_entries.items():
            day_total = 0
            for entry in day_entries:
                if entry.duration_hours:
                    day_total += entry.duration_hours

            day_hours[day_date] += day_total
            project_hours[project_id] += day_total
            total_hours += day_total

    # Display report
    console.print(
        f"[bold]Weekly Work Report ({start_of_week.strftime('%b %d')} - {end_of_week.strftime('%b %d, %Y')})[/bold]"
    )

    # Create summary table
    table = Table(title="Weekly Summary", box=box.ROUNDED)
    table.add_column("Project", style="bold")

    # Add columns for each day of the week
    for day_date in days_in_week:
        table.add_column(day_date.strftime("%a %d"), style="cyan")

    table.add_column("Total", style="green bold")

    # Add rows for each project
    for project_id, project in projects_dict.items():
        row = [project.name]

        for day_date in days_in_week:
            if day_date in entries_by_project[project_id]:
                day_total = 0
                for entry in entries_by_project[project_id][day_date]:
                    if entry.duration_hours:
                        day_total += entry.duration_hours
                row.append(f"{day_total:.2f}")
            else:
                row.append("-")

        row.append(f"{project_hours[project_id]:.2f}")
        table.add_row(*row)

    # Add totals row
    total_row = ["TOTAL"]
    for day_date in days_in_week:
        total_row.append(
            f"{day_hours[day_date]:.2f}" if day_hours[day_date] > 0 else "-"
        )
    total_row.append(f"{total_hours:.2f}")
    table.add_row(*total_row, style="bold")

    console.print(table)

    # Print billing information if applicable
    has_billing = False
    for project_id, project in projects_dict.items():
        if (
            project.is_billed_hourly
            and project.hour_rate
            and project_hours[project_id] > 0
        ):
            has_billing = True
            # Convert float to Decimal for multiplication with Decimal
            amount = Decimal(str(project_hours[project_id])) * project.hour_rate
            console.print(
                f"[bold]{project.name}[/bold]: {project_hours[project_id]:.2f} hours × ${project.hour_rate}/hour = ${amount:.2f}"
            )

    if has_billing:
        console.print("")

    console.print(f"[bold]Total Hours: {total_hours:.2f}[/bold]")
