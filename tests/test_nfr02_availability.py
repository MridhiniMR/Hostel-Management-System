from datetime import datetime

from hms.availability import monitor


def test_service_hours_are_17_hours_per_day():
    start = datetime(2026, 10, 30, 0, 0)
    end = datetime(2026, 10, 31, 0, 0)

    intervals = list(monitor.service_intervals(start, end))

    total_seconds = sum(
        (interval_end - interval_start).total_seconds()
        for interval_start, interval_end in intervals
    )

    assert total_seconds == 17 * 60 * 60


def test_availability_is_100_percent_without_incidents(tmp_path, monkeypatch):
    monkeypatch.setattr(monitor, "DB_PATH", tmp_path / "test_availability.db")

    monitor.initialize_database()

    start = datetime(2026, 10, 30, 6, 0)
    end = datetime(2026, 10, 30, 23, 0)

    result = monitor.calculate_availability(start, end)

    assert result["availability_percent"] == 100.0
    assert result["target_met"] is True


def test_downtime_reduces_availability(tmp_path, monkeypatch):
    monkeypatch.setattr(monitor, "DB_PATH", tmp_path / "test_availability.db")

    monitor.initialize_database()

    monitor.record_incident(
        datetime(2026, 10, 30, 10, 0),
        "Simulated application outage",
    )
    monitor.record_recovery(datetime(2026, 10, 30, 11, 0))

    result = monitor.calculate_availability(
        datetime(2026, 10, 30, 6, 0),
        datetime(2026, 10, 30, 23, 0),
    )

    assert result["unplanned_downtime_hours"] == 1.0
    assert result["availability_percent"] == round((16 / 17) * 100, 3)


def test_maintenance_is_excluded_from_availability(tmp_path, monkeypatch):
    monkeypatch.setattr(monitor, "DB_PATH", tmp_path / "test_availability.db")

    monitor.initialize_database()

    monitor.add_maintenance(
        starts_at=datetime(2026, 10, 30, 10, 0),
        ends_at=datetime(2026, 10, 30, 12, 0),
        description="Announced database maintenance",
        announced_at=datetime(2026, 10, 29, 12, 0),
    )

    result = monitor.calculate_availability(
        datetime(2026, 10, 30, 6, 0),
        datetime(2026, 10, 30, 23, 0),
    )

    assert result["planned_maintenance_hours"] == 2.0
    assert result["availability_percent"] == 100.0

def test_overlapping_maintenance_is_not_double_counted(tmp_path, monkeypatch):
    monkeypatch.setattr(monitor, "DB_PATH", tmp_path / "test_availability.db")
    monitor.initialize_database()

    announced = datetime(2026, 10, 29, 12, 0)

    monitor.add_maintenance(
        datetime(2026, 10, 30, 10, 0),
        datetime(2026, 10, 30, 12, 0),
        "Maintenance A",
        announced,
    )
    monitor.add_maintenance(
        datetime(2026, 10, 30, 11, 0),
        datetime(2026, 10, 30, 13, 0),
        "Maintenance B",
        announced,
    )

    result = monitor.calculate_availability(
        datetime(2026, 10, 30, 6, 0),
        datetime(2026, 10, 30, 23, 0),
    )

    assert result["planned_maintenance_hours"] == 3.0
    assert result["availability_percent"] == 100.0


def test_overlapping_incidents_are_not_double_counted(tmp_path, monkeypatch):
    monkeypatch.setattr(monitor, "DB_PATH", tmp_path / "test_availability.db")
    monitor.initialize_database()

    monitor.record_incident(
        datetime(2026, 10, 30, 10, 0),
        "First outage",
    )
    monitor.record_recovery(datetime(2026, 10, 30, 12, 0))

    monitor.record_incident(
        datetime(2026, 10, 30, 11, 0),
        "Second outage",
    )
    monitor.record_recovery(datetime(2026, 10, 30, 13, 0))

    result = monitor.calculate_availability(
        datetime(2026, 10, 30, 6, 0),
        datetime(2026, 10, 30, 23, 0),
    )

    assert result["unplanned_downtime_hours"] == 3.0


def test_late_announced_maintenance_counts_as_downtime(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(
        monitor, "DB_PATH", tmp_path / "test_availability.db"
    )
    monitor.initialize_database()

    # Maintenance starts at 10 AM but is announced at 11 AM.
    monitor.add_maintenance(
        starts_at=datetime(2026, 10, 30, 10, 0),
        ends_at=datetime(2026, 10, 30, 12, 0),
        description="Late announcement",
        announced_at=datetime(2026, 10, 30, 11, 0),
    )

    # Record the interruption from 10 AM to noon.
    monitor.record_incident(
        datetime(2026, 10, 30, 10, 0),
        "Service interruption",
    )
    monitor.record_recovery(datetime(2026, 10, 30, 12, 0))

    result = monitor.calculate_availability(
        datetime(2026, 10, 30, 6, 0),
        datetime(2026, 10, 30, 23, 0),
    )

    assert result["planned_maintenance_hours"] == 0.0
    assert result["unplanned_downtime_hours"] == 2.0


def test_outage_overlapping_maintenance_counts_only_uncovered_time(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(
        monitor, "DB_PATH", tmp_path / "test_availability.db"
    )
    monitor.initialize_database()

    monitor.add_maintenance(
        starts_at=datetime(2026, 10, 30, 10, 0),
        ends_at=datetime(2026, 10, 30, 12, 0),
        description="Announced maintenance",
        announced_at=datetime(2026, 10, 29, 12, 0),
    )

    # Outage lasts from 9 AM to 1 PM.
    monitor.record_incident(
        datetime(2026, 10, 30, 9, 0),
        "Application outage",
    )
    monitor.record_recovery(datetime(2026, 10, 30, 13, 0))

    result = monitor.calculate_availability(
        datetime(2026, 10, 30, 6, 0),
        datetime(2026, 10, 30, 23, 0),
    )

    assert result["planned_maintenance_hours"] == 2.0
    assert result["unplanned_downtime_hours"] == 2.0
    assert result["availability_percent"] == round((13 / 15) * 100, 3)
