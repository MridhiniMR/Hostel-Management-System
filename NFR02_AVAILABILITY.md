# NFR-02: System Availability and Recovery



## 1. Objective



The Hostel Management System aims to achieve at least 99% monthly availability during scheduled service hours.



## 2. Scheduled Service Hours



- Service days: Every day

- Start time: 6:00 AM

- End time: 11:00 PM

- Total scheduled service: 17 hours per day

- Time basis: Local machine time



Announced planned maintenance is excluded from the availability calculation.



## 3. Availability Calculation



Availability is calculated using:



Availability (%) = ((Eligible Service Time - Unplanned Downtime) / Eligible Service Time) × 100



Where:



- Eligible Service Time = Scheduled Service Time - Announced Planned Maintenance

- Unplanned Downtime = Recorded outage duration excluding overlapping planned maintenance.



The monthly target is 99%.



## 4. Monitoring Implementation



The monitoring module is located at:



`hms/availability/monitor.py`



The monitoring process:



1. Sends periodic requests to the application's `/health` endpoint.

2. Checks both application and database health.

3. Records an incident when a health check fails.

4. Records recovery when the health check succeeds again.

5. Stores incident and maintenance records in a separate SQLite database named `availability.db`.

6. Generates monthly availability reports.



Default monitoring interval: 60 seconds.



## 5. Recovery Procedure



If the health check fails:



1. Open the application terminal.

2. Check whether the FastAPI/Uvicorn process is running.

3. If it has stopped, restart the application using:



&#x20;  `python -m uvicorn hms.main:app --host 127.0.0.1 --port 8000`



4. Open `/health` in a browser and verify that both application and database status are OK.

5. The monitoring process records recovery on its next successful health check.

6. Review the incident record and monthly availability report.



## 6. Test Evidence



The following functional tests were performed:



- Health endpoint reports application and database status.

- Application outage is detected.

- Application recovery is recorded.

- Overlapping incidents are not double-counted.

- Overlapping maintenance windows are not double-counted.

- Late-announced maintenance is treated as unplanned downtime.

- Outage time overlapping announced maintenance is excluded appropriately.



A simulated outage was recorded on October 30, 2026:



- Detected outage: 10:20:43 PM

- Detected recovery: 10:21:45 PM

- Approximate duration: 62 seconds



The October 2026 test report calculated 99.997% availability against the 99% target.



This result is functional test evidence only and does not establish actual production availability for the entire month.



## 7. Limitations and Future Improvements



- Monitoring currently runs as a separate foreground process.

- Monitoring records detection and recovery timestamps, not the exact underlying failure and recovery times.

- Monitoring checks only during scheduled service hours.

- Monthly availability must be reviewed using accumulated operational records.

- A production deployment should run the monitor as a persistent service and retain monitoring data securely.



