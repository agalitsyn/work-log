from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from app.models import Project, WorkEntry


def test_full_workflow(test_db):
    """s
    Test a full workflow as described in the requirements:
    1. Create multiple projects
    2. Start and stop work on different projects
    3. Generate daily and weekly reports
    """
    # 1. Create projects with different billing configurations
    project1 = Project(
        name="Project A", is_billed_hourly=True, hour_rate=Decimal("100.00")
    )
    project2 = Project(name="Project B", is_billed_hourly=False)
    project3 = Project(
        name="Project C", is_billed_hourly=True, hour_rate=Decimal("75.50")
    )

    project1_id = test_db.create_project(project1)
    project2_id = test_db.create_project(project2)
    project3_id = test_db.create_project(project3)

    assert project1_id > 0
    assert project2_id > 0
    assert project3_id > 0

    # Verify projects are created correctly
    projects = test_db.get_all_projects()
    assert len(projects) == 3

    # 2. Mock a day of work with several tasks
    # For testing, we'll use fixed times instead of actual time.now()
    base_time = datetime(2023, 5, 1, 9, 0, 0)  # Start at 9 AM

    # Start work on Project A
    entry1 = WorkEntry(
        project_id=project1_id,
        description="Task 1 for Project A",
        start_time=base_time,
        end_time=base_time + timedelta(hours=2),  # 2 hours
    )
    test_db.create_work_entry(entry1)

    # Start work on Project B
    entry2 = WorkEntry(
        project_id=project2_id,
        description="Task 1 for Project B",
        start_time=base_time + timedelta(hours=2),
        end_time=base_time + timedelta(hours=3, minutes=30),  # 1.5 hours
    )
    test_db.create_work_entry(entry2)

    # Back to Project A
    entry3 = WorkEntry(
        project_id=project1_id,
        description="Task 2 for Project A",
        start_time=base_time + timedelta(hours=3, minutes=30),
        end_time=base_time + timedelta(hours=5),  # 1.5 hours
    )
    test_db.create_work_entry(entry3)

    # Work on Project C
    entry4 = WorkEntry(
        project_id=project3_id,
        description="Task 1 for Project C",
        start_time=base_time + timedelta(hours=5),
        end_time=base_time + timedelta(hours=7),  # 2 hours
    )
    test_db.create_work_entry(entry4)

    # 3. Test daily report
    day_entries = test_db.get_entries_for_day(base_time.date())
    assert len(day_entries) == 4

    # Calculate and verify totals by project
    hours_by_project = {project1_id: 0, project2_id: 0, project3_id: 0}
    for entry, project in day_entries:
        project_id = (
            entry.project_id
        )  # Use the project_id from the entry, not from the project
        if project_id not in hours_by_project:
            hours_by_project[project_id] = 0
        hours_by_project[project_id] += entry.duration_hours

    # Map original project IDs to the expected hours
    expected_hours = {
        project1_id: 3.5,  # 2 + 1.5 hours
        project2_id: 1.5,
        project3_id: 2.0,
    }

    # Verify each project's hours
    for pid, expected in expected_hours.items():
        assert hours_by_project[pid] == pytest.approx(expected)

    # 4. Add entries for the next day
    next_day = base_time + timedelta(days=1)

    entry5 = WorkEntry(
        project_id=project1_id,
        description="Task 3 for Project A",
        start_time=next_day,
        end_time=next_day + timedelta(hours=3),  # 3 hours
    )
    test_db.create_work_entry(entry5)

    entry6 = WorkEntry(
        project_id=project3_id,
        description="Task 2 for Project C",
        start_time=next_day + timedelta(hours=3),
        end_time=next_day + timedelta(hours=6),  # 3 hours
    )
    test_db.create_work_entry(entry6)

    # 5. Test weekly report
    week_entries = test_db.get_entries_for_week(base_time.date())
    assert len(week_entries) == 6

    # Calculate weekly totals
    weekly_hours_by_project = {project1_id: 0, project2_id: 0, project3_id: 0}
    for entry, project in week_entries:
        project_id = (
            entry.project_id
        )  # Use the project_id from the entry, not from the project
        if project_id not in weekly_hours_by_project:
            weekly_hours_by_project[project_id] = 0
        weekly_hours_by_project[project_id] += entry.duration_hours

    # Map original project IDs to the expected weekly hours
    expected_weekly_hours = {
        project1_id: 6.5,  # 3.5 + 3 hours
        project2_id: 1.5,
        project3_id: 5.0,  # 2 + 3 hours
    }

    # Verify each project's weekly hours
    for pid, expected in expected_weekly_hours.items():
        assert weekly_hours_by_project[pid] == pytest.approx(expected)

    # 6. Test billing calculations
    billing_totals = {}
    for project_id, hours in weekly_hours_by_project.items():
        project = test_db.get_project(project_id)
        if project.is_billed_hourly and project.hour_rate:
            # Convert hours (float) to Decimal for multiplication with Decimal
            billing_totals[project.name] = Decimal(str(hours)) * project.hour_rate

    # Verify billing calculations
    assert billing_totals["Project A"] == pytest.approx(
        Decimal("650.00")
    )  # 6.5 hours × $100
    assert billing_totals["Project C"] == pytest.approx(
        Decimal("377.50")
    )  # 5 hours × $75.50
    assert "Project B" not in billing_totals  # Not billed hourly


def test_active_work_entry(test_db):
    """Test tracking active work without an end time."""
    # Create a project
    project = Project(name="Test Project")
    project_id = test_db.create_project(project)

    # Start a task but don't end it
    active_entry = WorkEntry(
        project_id=project_id,
        description="Active task",
        start_time=datetime.now(),
    )
    entry_id = test_db.create_work_entry(active_entry)

    # Get the active entry
    retrieved_entry = test_db.get_active_work_entry()
    assert retrieved_entry is not None
    assert retrieved_entry.id == entry_id
    assert retrieved_entry.description == "Active task"
    assert retrieved_entry.end_time is None

    # Finish the task
    retrieved_entry.end_time = datetime.now()
    test_db.update_work_entry(retrieved_entry)

    # Should be no active entry now
    assert test_db.get_active_work_entry() is None


def test_project_modification(test_db):
    """Test creating, updating, and deleting projects."""
    # Create a project
    project = Project(name="Original Project", is_billed_hourly=False)
    project_id = test_db.create_project(project)

    # Update the project
    retrieved_project = test_db.get_project(project_id)
    retrieved_project.name = "Updated Project"
    retrieved_project.is_billed_hourly = True
    retrieved_project.hour_rate = Decimal("125.75")

    assert test_db.update_project(retrieved_project)

    # Verify the update
    updated_project = test_db.get_project(project_id)
    assert updated_project.name == "Updated Project"
    assert updated_project.is_billed_hourly
    assert updated_project.hour_rate == Decimal("125.75")

    # Delete the project
    assert test_db.delete_project(project_id)
    assert test_db.get_project(project_id) is None
