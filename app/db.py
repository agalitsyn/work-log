import os
import sqlite3
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Tuple

from .models import Project, WorkEntry


class Database:
    def __init__(self, db_path: str = None):
        if db_path is None:
            home_dir = os.path.expanduser("~")
            db_dir = os.path.join(home_dir, ".work-log")
            os.makedirs(db_dir, exist_ok=True)
            db_path = os.path.join(db_dir, "work-log.db")

        self.db_path = db_path
        self._init_db()

    def _create_project_from_row(self, row):
        """Helper method to create a Project object from a database row with proper Decimal conversion"""
        hour_rate = None
        if row["hour_rate"] is not None:
            hour_rate = Decimal(str(row["hour_rate"]))

        # Get the ID field from either 'id' or 'p_id'
        try:
            project_id = row["id"]
        except IndexError:
            project_id = row["p_id"]

        # Get the name field from either 'name' or 'p_name'
        try:
            project_name = row["name"]
        except IndexError:
            project_name = row["p_name"]

        return Project(
            id=project_id,
            name=project_name,
            is_billed_hourly=bool(row["is_billed_hourly"]),
            hour_rate=hour_rate,
        )

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Create projects table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    is_billed_hourly INTEGER DEFAULT 0,
                    hour_rate REAL
                )
            """)

            # Create work entries table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS work_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    description TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    FOREIGN KEY (project_id) REFERENCES projects (id)
                )
            """)

            conn.commit()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # Project methods
    def create_project(self, project: Project) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Convert Decimal to float for SQLite compatibility
            hour_rate = (
                float(project.hour_rate) if project.hour_rate is not None else None
            )
            cursor.execute(
                """
                INSERT INTO projects (name, is_billed_hourly, hour_rate)
                VALUES (?, ?, ?)
                """,
                (project.name, int(project.is_billed_hourly), hour_rate),
            )
            conn.commit()
            return cursor.lastrowid

    def get_project(self, project_id: int) -> Optional[Project]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
            row = cursor.fetchone()

            if row:
                return self._create_project_from_row(row)
            return None

    def get_project_by_name(self, name: str) -> Optional[Project]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM projects WHERE name = ?", (name,))
            row = cursor.fetchone()

            if row:
                return self._create_project_from_row(row)
            return None

    def get_all_projects(self) -> List[Project]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM projects ORDER BY name")
            rows = cursor.fetchall()

            projects = []
            for row in rows:
                projects.append(self._create_project_from_row(row))

            return projects

    def update_project(self, project: Project) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Convert Decimal to float for SQLite compatibility
            hour_rate = (
                float(project.hour_rate) if project.hour_rate is not None else None
            )
            cursor.execute(
                """
                UPDATE projects
                SET name = ?, is_billed_hourly = ?, hour_rate = ?
                WHERE id = ?
                """,
                (
                    project.name,
                    int(project.is_billed_hourly),
                    hour_rate,
                    project.id,
                ),
            )
            conn.commit()
            return cursor.rowcount > 0

    def delete_project(self, project_id: int) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM projects WHERE id = ?", (project_id,))
            conn.commit()
            return cursor.rowcount > 0

    # Work entry methods
    def create_work_entry(self, entry: WorkEntry) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO work_entries (project_id, description, start_time, end_time)
                VALUES (?, ?, ?, ?)
                """,
                (
                    entry.project_id,
                    entry.description,
                    entry.start_time.isoformat() if entry.start_time else None,
                    entry.end_time.isoformat() if entry.end_time else None,
                ),
            )
            conn.commit()
            return cursor.lastrowid

    def get_work_entry(self, entry_id: int) -> Optional[WorkEntry]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM work_entries WHERE id = ?", (entry_id,))
            row = cursor.fetchone()

            if row:
                return WorkEntry(
                    id=row["id"],
                    project_id=row["project_id"],
                    description=row["description"],
                    start_time=datetime.fromisoformat(row["start_time"])
                    if row["start_time"]
                    else None,
                    end_time=datetime.fromisoformat(row["end_time"])
                    if row["end_time"]
                    else None,
                )
            return None

    def get_active_work_entry(self) -> Optional[WorkEntry]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM work_entries WHERE end_time IS NULL")
            row = cursor.fetchone()

            if row:
                return WorkEntry(
                    id=row["id"],
                    project_id=row["project_id"],
                    description=row["description"],
                    start_time=datetime.fromisoformat(row["start_time"])
                    if row["start_time"]
                    else None,
                    end_time=datetime.fromisoformat(row["end_time"])
                    if row["end_time"]
                    else None,
                )
            return None

    def update_work_entry(self, entry: WorkEntry) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE work_entries
                SET project_id = ?, description = ?, start_time = ?, end_time = ?
                WHERE id = ?
                """,
                (
                    entry.project_id,
                    entry.description,
                    entry.start_time.isoformat() if entry.start_time else None,
                    entry.end_time.isoformat() if entry.end_time else None,
                    entry.id,
                ),
            )
            conn.commit()
            return cursor.rowcount > 0

    def delete_work_entry(self, entry_id: int) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM work_entries WHERE id = ?", (entry_id,))
            conn.commit()
            return cursor.rowcount > 0

    def get_entries_for_day(self, day: date) -> List[Tuple[WorkEntry, Project]]:
        start_of_day = datetime.combine(day, datetime.min.time())
        end_of_day = datetime.combine(day, datetime.max.time())

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT e.*, p.id as p_id, p.name as p_name, p.is_billed_hourly, p.hour_rate
                FROM work_entries e
                JOIN projects p ON e.project_id = p.id
                WHERE (e.start_time BETWEEN ? AND ?) OR
                      (e.end_time BETWEEN ? AND ?) OR
                      (e.start_time < ? AND (e.end_time > ? OR e.end_time IS NULL))
                ORDER BY e.start_time
                """,
                (
                    start_of_day.isoformat(),
                    end_of_day.isoformat(),
                    start_of_day.isoformat(),
                    end_of_day.isoformat(),
                    start_of_day.isoformat(),
                    end_of_day.isoformat(),
                ),
            )
            rows = cursor.fetchall()

            results = []
            for row in rows:
                entry = WorkEntry(
                    id=row["id"],
                    project_id=row["project_id"],
                    description=row["description"],
                    start_time=datetime.fromisoformat(row["start_time"])
                    if row["start_time"]
                    else None,
                    end_time=datetime.fromisoformat(row["end_time"])
                    if row["end_time"]
                    else None,
                )

                project = self._create_project_from_row(row)

                results.append((entry, project))

            return results

    def get_entries_for_week(
        self, date_in_week: date
    ) -> List[Tuple[WorkEntry, Project]]:
        # Find the start of the week (Monday)
        start_of_week = date_in_week - timedelta(days=date_in_week.weekday())
        end_of_week = start_of_week + timedelta(days=6)

        start_datetime = datetime.combine(start_of_week, datetime.min.time())
        end_datetime = datetime.combine(end_of_week, datetime.max.time())

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT e.*, p.id as p_id, p.name as p_name, p.is_billed_hourly, p.hour_rate
                FROM work_entries e
                JOIN projects p ON e.project_id = p.id
                WHERE (e.start_time BETWEEN ? AND ?) OR
                      (e.end_time BETWEEN ? AND ?) OR
                      (e.start_time < ? AND (e.end_time > ? OR e.end_time IS NULL))
                ORDER BY e.start_time
                """,
                (
                    start_datetime.isoformat(),
                    end_datetime.isoformat(),
                    start_datetime.isoformat(),
                    end_datetime.isoformat(),
                    start_datetime.isoformat(),
                    end_datetime.isoformat(),
                ),
            )
            rows = cursor.fetchall()

            results = []
            for row in rows:
                entry = WorkEntry(
                    id=row["id"],
                    project_id=row["project_id"],
                    description=row["description"],
                    start_time=datetime.fromisoformat(row["start_time"])
                    if row["start_time"]
                    else None,
                    end_time=datetime.fromisoformat(row["end_time"])
                    if row["end_time"]
                    else None,
                )

                project = self._create_project_from_row(row)

                results.append((entry, project))

            return results
