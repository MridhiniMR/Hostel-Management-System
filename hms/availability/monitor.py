
from __future__ import annotations

import sqlite3
from datetime import date, datetime, time, timedelta
from pathlib import Path

# Separate database for availability monitoring.
DB_PATH = Path("availability.db")

# Scheduled service hours: 6 AM to 11 PM, local machine time.
SERVICE_START = time(6, 0)
SERVICE_END = time(23, 0)

AVAILABILITY_TARGET = 99.0


def get_connection():
    """Open the availability monitoring database."""
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    """Create tables for outages and planned maintenance."""
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS incidents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                recovered_at TEXT,
                description TEXT
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS maintenance_windows (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                starts_at TEXT NOT NULL,
                ends_at TEXT NOT NULL,
                announced_at TEXT NOT NULL,
                description TEXT NOT NULL
            )
        """)


def record_incident(started_at: datetime, description: str):
    """Record the beginning of an unplanned outage."""
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO incidents (started_at, description)
            VALUES (?, ?)
            """,
            (started_at.isoformat(), description),
        )


def record_recovery(recovered_at: datetime):
    """Close the most recent unresolved outage."""
    with get_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE incidents
            SET recovered_at = ?
            WHERE id = (
                SELECT id FROM incidents
                WHERE recovered_at IS NULL
                ORDER BY started_at DESC
                LIMIT 1
            )
            """,
            (recovered_at.isoformat(),),
        )

        if cursor.rowcount == 0:
            raise ValueError("No unresolved incident exists.")


def add_maintenance(
    starts_at: datetime,
    ends_at: datetime,
    description: str,
    announced_at: datetime | None = None,
):
    """Register a planned maintenance window."""
    if ends_at <= starts_at:
        raise ValueError("Maintenance end must be after its start.")

    announced_at = announced_at or datetime.now().astimezone()

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO maintenance_windows
            (starts_at, ends_at, announced_at, description)
            VALUES (?, ?, ?, ?)
            """,
            (
                starts_at.isoformat(),
                ends_at.isoformat(),
                announced_at.isoformat(),
                description,
            ),
        )


def _merge_intervals(intervals):
    """Merge overlapping or touching intervals."""
    if not intervals:
        return []

    intervals = sorted(intervals, key=lambda item: item[0])
    merged = [list(intervals[0])]

    for current_start, current_end in intervals[1:]:
        previous = merged[-1]

        if current_start <= previous[1]:
            previous[1] = max(previous[1], current_end)
        else:
            merged.append([current_start, current_end])

    return [(start, end) for start, end in merged]


def _duration_seconds(intervals):
    """Calculate total duration without double-counting."""
    return sum(
        (end - start).total_seconds()
        for start, end in intervals
    )


def service_intervals(start: datetime, end: datetime):
    """Generate daily scheduled service intervals."""
    current_date = start.date()

    while current_date <= end.date():
        interval_start = datetime.combine(
            current_date, SERVICE_START, tzinfo=start.tzinfo
        )
        interval_end = datetime.combine(
            current_date, SERVICE_END, tzinfo=start.tzinfo
        )

        actual_start = max(start, interval_start)
        actual_end = min(end, interval_end)

        if actual_end > actual_start:
            yield actual_start, actual_end

        current_date += timedelta(days=1)


def overlap_seconds(
    first_start: datetime,
    first_end: datetime,
    second_start: datetime,
    second_end: datetime,
) -> float:
    """Return overlapping duration between two intervals."""
    overlap_start = max(first_start, second_start)
    overlap_end = min(first_end, second_end)

    if overlap_end <= overlap_start:
        return 0.0

    return (overlap_end - overlap_start).total_seconds()


def calculate_availability(
    period_start: datetime,
    period_end: datetime,
) -> dict:
    """
    Calculate availability during scheduled service hours.

    Only maintenance announced before its scheduled start is excluded.
    Overlapping maintenance and incidents are counted once.
    """
    if period_end <= period_start:
        raise ValueError("Period end must be after period start.")

    if (period_start.tzinfo is None) != (period_end.tzinfo is None):
        raise ValueError("Period datetimes must use consistent timezones.")

    with get_connection() as connection:
        incidents = connection.execute(
            "SELECT * FROM incidents"
        ).fetchall()

        maintenance = connection.execute(
            "SELECT * FROM maintenance_windows"
        ).fetchall()

    scheduled_seconds = 0.0
    maintenance_seconds = 0.0
    downtime_seconds = 0.0

    for interval_start, interval_end in service_intervals(
        period_start, period_end
    ):
        scheduled_seconds += (
            interval_end - interval_start
        ).total_seconds()

        # Collect announced maintenance overlapping this service interval.
        maintenance_intervals = []

        for window in maintenance:
            starts_at = datetime.fromisoformat(window["starts_at"])
            ends_at = datetime.fromisoformat(window["ends_at"])
            announced_at = datetime.fromisoformat(window["announced_at"])

            if (starts_at.tzinfo is None) != (period_start.tzinfo is None):
                raise ValueError("Maintenance and report timezones differ.")

            if announced_at > starts_at:
                continue

            clipped_start = max(interval_start, starts_at)
            clipped_end = min(interval_end, ends_at)

            if clipped_end > clipped_start:
                maintenance_intervals.append(
                    (clipped_start, clipped_end)
                )

        maintenance_intervals = _merge_intervals(
            maintenance_intervals
        )

        maintenance_seconds += _duration_seconds(
            maintenance_intervals
        )

        # Collect and merge outage intervals.
        incident_intervals = []

        for incident in incidents:
            incident_start = datetime.fromisoformat(
                incident["started_at"]
            )

            incident_end = (
                datetime.fromisoformat(incident["recovered_at"])
                if incident["recovered_at"]
                else period_end
            )

            if (incident_start.tzinfo is None) != (
                period_start.tzinfo is None
            ):
                raise ValueError("Incident and report timezones differ.")

            clipped_start = max(interval_start, incident_start)
            clipped_end = min(interval_end, incident_end)

            if clipped_end > clipped_start:
                incident_intervals.append(
                    (clipped_start, clipped_end)
                )

        incident_intervals = _merge_intervals(
            incident_intervals
        )

        # Count only outage time that is not excluded maintenance.
        for outage_start, outage_end in incident_intervals:
            outage_duration = (outage_end - outage_start).total_seconds()

            excluded_overlap = sum(
                overlap_seconds(
                    outage_start,
                    outage_end,
                    maintenance_start,
                    maintenance_end,
                )
                for maintenance_start, maintenance_end
                in maintenance_intervals
            )

            downtime_seconds += max(
                0.0,
                outage_duration - excluded_overlap,
            )

    eligible_seconds = max(
        0.0,
        scheduled_seconds - maintenance_seconds,
    )

    availability = (
        100.0
        if eligible_seconds == 0
        else (
            max(0.0, eligible_seconds - downtime_seconds)
            / eligible_seconds
        ) * 100
    )

    return {
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "scheduled_hours": round(scheduled_seconds / 3600, 2),
        "planned_maintenance_hours": round(
            maintenance_seconds / 3600, 2
        ),
        "unplanned_downtime_hours": round(
            downtime_seconds / 3600, 2
        ),
        "availability_percent": round(availability, 3),
        "target_percent": AVAILABILITY_TARGET,
        "target_met": availability >= AVAILABILITY_TARGET,
    }


import argparse
import json
import time as clock
from urllib.error import URLError, HTTPError
from urllib.request import urlopen


def get_open_incident():
    """Return the latest unresolved incident, if one exists."""
    with get_connection() as connection:
        return connection.execute(
            """
            SELECT * FROM incidents
            WHERE recovered_at IS NULL
            ORDER BY started_at DESC
            LIMIT 1
            """
        ).fetchone()


def check_application(url: str, timeout: int = 5) -> bool:
    """Return True only when the application and database are healthy."""
    try:
        with urlopen(url, timeout=timeout) as response:
            if response.status != 200:
                return False

            data = json.loads(response.read().decode("utf-8"))

            return (
                data.get("status") == "ok"
                and data.get("database") == "ok"
            )

    except (URLError, HTTPError, TimeoutError, ValueError, OSError):
        return False


def monitor_application(url: str, interval: int = 60):
    """Continuously monitor the application during service hours."""
    if interval < 1:
        raise ValueError("Monitoring interval must be at least 1 second.")

    initialize_database()

    print(f"Monitoring: {url}")
    print(f"Check interval: {interval} seconds")
    print("Service hours: 6:00 AM to 11:00 PM")
    print("Press Ctrl+C to stop monitoring.")

    try:
        while True:
            now = datetime.now()

            # Do not count time outside scheduled service hours.
            if not (SERVICE_START <= now.time() < SERVICE_END):
                clock.sleep(interval)
                continue

            healthy = check_application(url)
            open_incident = get_open_incident()

            if healthy:
                if open_incident:
                    record_recovery(now)
                    print(f"[RECOVERED] {now.isoformat()}")
                else:
                    print(f"[HEALTHY] {now.isoformat()}")

            else:
                if not open_incident:
                    record_incident(
                        now,
                        f"Health check failed for {url}",
                    )
                    print(f"[OUTAGE DETECTED] {now.isoformat()}")
                else:
                    print(f"[STILL DOWN] {now.isoformat()}")

            clock.sleep(interval)

    except KeyboardInterrupt:
        print("\nMonitoring stopped by user.")


def monthly_report(year: int, month: int) -> dict:
    """Generate an availability report for a calendar month."""
    if not 1 <= month <= 12:
        raise ValueError("Month must be between 1 and 12.")

    period_start = datetime(year, month, 1)

    if month == 12:
        period_end = datetime(year + 1, 1, 1)
    else:
        period_end = datetime(year, month + 1, 1)

    return calculate_availability(period_start, period_end)


def main():
    parser = argparse.ArgumentParser(
        description="Hostel Management System availability monitor"
    )

    parser.add_argument(
        "--url",
        default="http://127.0.0.1:8000/health",
        help="Application health-check URL",
    )

    parser.add_argument(
        "--interval",
        type=int,
        default=60,
        help="Seconds between health checks (default: 60)",
    )

    parser.add_argument(
        "--report-month",
        help="Generate a monthly report in YYYY-MM format instead of monitoring",
    )

    args = parser.parse_args()

    if args.report_month:
        try:
            year_text, month_text = args.report_month.split("-")
            report = monthly_report(int(year_text), int(month_text))
            print(json.dumps(report, indent=4))
        except (ValueError, TypeError):
            parser.error("--report-month must use YYYY-MM format")
    else:
        monitor_application(args.url, args.interval)


if __name__ == "__main__":
    main()
