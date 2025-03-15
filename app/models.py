from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional


class Project:
    def __init__(
        self,
        id: Optional[int] = None,
        name: str = "",
        is_billed_hourly: bool = False,
        hour_rate: Optional[Decimal] = None,
    ):
        self.id = id
        self.name = name
        self.is_billed_hourly = is_billed_hourly
        self.hour_rate = hour_rate

    def __str__(self):
        return f"{self.name}"


class WorkEntry:
    def __init__(
        self,
        id: Optional[int] = None,
        project_id: int = 0,
        description: str = "",
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ):
        self.id = id
        self.project_id = project_id
        self.description = description
        self.start_time = start_time
        self.end_time = end_time

    @property
    def duration(self) -> Optional[timedelta]:
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None

    @property
    def duration_hours(self) -> Optional[float]:
        if self.duration:
            return self.duration.total_seconds() / 3600
        return None

    def __str__(self):
        return (
            f"{self.description} ({self.duration_hours:.2f}h)"
            if self.duration_hours
            else f"{self.description} (in progress)"
        )
