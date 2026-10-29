# Sprint 2 — two-minute video script

Goal: a working product, about 2 minutes. Save the file as `Sprint2_Demo.mp4` in this folder.
Record on Windows with Win + G (Xbox Game Bar, "Capture"), or with OBS Studio.

Before recording: start the app (`uvicorn hms.main:app`), open http://127.0.0.1:8000/login,
and have one admin account ready. Use an empty database so the demo is clean.

| Time | What to show | What to say |
|---|---|---|
| 0:00 | Login page, sign in as administrator | "Hostel Management System, Sprint 2. I'm logging in as the warden." |
| 0:10 | Create a student and a room (capacity 1) | "Student and room records (FR-02, FR-04)." |
| 0:25 | Allocations page: choose student, choose room, Allocate | "A valid allocation takes three data-entry steps (NFR-04)." |
| 0:45 | Room list showing occupancy 1/1 | "Occupancy updates immediately (FR-08)." |
| 0:55 | Try to allocate a second student to the full room, show the error | "The full room is rejected and nothing changes (FR-06, NFR-03)." |
| 1:10 | Try to allocate the same student again, show the error | "Duplicate active allocations are blocked." |
| 1:20 | Move or deallocate the allocation | "Modify and deallocate (FR-07)." |
| 1:35 | Log in as a student, open My Allocation | "Students see only their own allocation (FR-09)." |
| 1:50 | Terminal: `python -m pytest -q` passing, then the GitHub Actions green tick | "All automated tests pass, including the atomicity tests for NFR-03." |
| 2:00 | End | |

Say out loud, once, the deviations from the SRS/SAD/Test Plan (see the notes you wrote).
