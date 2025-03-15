import pytest
from typer.testing import CliRunner
import os
import tempfile
from decimal import Decimal
from datetime import datetime, timedelta
import time

from app.cli import app
from app.db import Database
from app.models import Project, WorkEntry


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def mock_db_path():
    # Create a temporary file for the test database
    temp_file = tempfile.NamedTemporaryFile(delete=False)
    temp_file.close()
    
    # Set up a test database
    db = Database(temp_file.name)
    
    # Create sample projects
    project1 = Project(name="CLI Project A", is_billed_hourly=True, hour_rate=Decimal("85.00"))
    project2 = Project(name="CLI Project B", is_billed_hourly=False)
    
    db.create_project(project1)
    db.create_project(project2)
    
    # Override the database instance in the CLI module (this is a bit hacky but works for testing)
    import app.cli
    app.cli.db = db
    
    yield temp_file.name
    
    # Clean up
    os.unlink(temp_file.name)


def test_project_commands(runner, mock_db_path):
    # Test listing projects
    result = runner.invoke(app, ["projects"])
    assert result.exit_code == 0
    assert "CLI Project A" in result.stdout
    assert "CLI Project B" in result.stdout
    
    # Test adding a project
    result = runner.invoke(app, ["project-add", "CLI Project C", "--hourly", "--rate", "120"])
    assert result.exit_code == 0
    assert "CLI Project C" in result.stdout
    
    # Verify project was added
    result = runner.invoke(app, ["projects"])
    assert "CLI Project C" in result.stdout
    assert "$120" in result.stdout  # Check rate is displayed
    
    # Test updating a project (assuming it has ID 3)
    result = runner.invoke(app, ["project-update", "3", "--name", "Updated Project C"])
    assert result.exit_code == 0
    
    # Verify update
    result = runner.invoke(app, ["projects"])
    assert "Updated Project C" in result.stdout


def test_work_tracking_commands(runner, mock_db_path):
    # Make sure no active work
    result = runner.invoke(app, ["status"])
    assert "No active work" in result.stdout
    
    # Start work on a project
    result = runner.invoke(app, ["start", "CLI Project A", "Test task for CLI Project A"])
    assert result.exit_code == 0
    assert "Started work" in result.stdout
    
    # Check status
    result = runner.invoke(app, ["status"])
    assert "Currently working on" in result.stdout
    assert "Test task for CLI Project A" in result.stdout
    
    # Wait a bit to have some elapsed time
    time.sleep(1)
    
    # Stop work
    result = runner.invoke(app, ["stop"])
    assert result.exit_code == 0
    assert "Stopped work" in result.stdout
    
    # Check no active work
    result = runner.invoke(app, ["status"])
    assert "No active work" in result.stdout


def test_reporting_commands(runner, mock_db_path):
    db = Database(mock_db_path)
    
    # Create some work entries for today
    project = db.get_project_by_name("CLI Project A")
    
    today = datetime.now()
    yesterday = today - timedelta(days=1)
    
    # Add work for yesterday
    entry1 = WorkEntry(
        project_id=project.id,
        description="Yesterday's task",
        start_time=yesterday.replace(hour=9, minute=0),
        end_time=yesterday.replace(hour=12, minute=0)  # 3 hours
    )
    db.create_work_entry(entry1)
    
    # Add work for today
    entry2 = WorkEntry(
        project_id=project.id,
        description="Today's task",
        start_time=today.replace(hour=9, minute=0),
        end_time=today.replace(hour=11, minute=30)  # 2.5 hours
    )
    db.create_work_entry(entry2)
    
    # Test today's report
    result = runner.invoke(app, ["today"])
    assert result.exit_code == 0
    assert "Today's task" in result.stdout
    assert "2.50" in result.stdout  # 2.5 hours
    
    # Test yesterday's report
    result = runner.invoke(app, ["yesterday"])
    assert result.exit_code == 0
    assert "Yesterday's task" in result.stdout
    assert "3.00" in result.stdout  # 3 hours
    
    # Test weekly report
    result = runner.invoke(app, ["week"])
    assert result.exit_code == 0
    assert "Weekly Work Report" in result.stdout
    assert "CLI Project A" in result.stdout
    assert "5.50" in result.stdout  # Total hours (3 + 2.5)
    
    # Instead of checking for the combined billing, check for individual entry billings
    assert "$255.00" in result.stdout  # Billing for yesterday (3 * 85)
    assert "$212.50" in result.stdout  # Billing for today (2.5 * 85)