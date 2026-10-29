# Execution evidence — TP-12 (NFR-03) and TP-13 (NFR-04)

The submitted Test Plan PDF keeps its original `Not Executed` statuses. This file is the
execution evidence for these two cases.

## TP-12 — Allocation transaction integrity (NFR-03)
- Precondition: database transaction support enabled; room near capacity.
- Action: force a failure during the allocation transaction.
- Automated tests (`tests/test_nfr03_atomicity.py`):
  - `test_tp12_forced_failure_mid_allocation_leaves_no_partial_state` — failure is forced after the
    allocation row is written and before commit. Result: no allocation row, occupancy unchanged,
    and the same allocation succeeds afterwards.
  - `test_tp12_session_is_rolled_back_by_service_on_unexpected_error` — the service itself rolls back.
  - `test_tp12_rejected_allocation_changes_no_capacity_state` — a full-room rejection changes nothing.
  - `test_nfr03_two_concurrent_requests_cannot_both_take_the_last_bed` — 4 simultaneous requests,
    1 bed: exactly 1 succeeds.
  - `test_nfr03_concurrent_moves_cannot_overfill_a_room` — 4 simultaneous moves, 1 free bed: exactly 1 succeeds.
- Expected: either the full allocation change commits or all related changes roll back; no partial state remains.
- Result: Pass (see BUG-001 for the defect found and fixed while running this case).
- Screenshot: (paste your own pytest screenshot here)

Implementation note (documented design choice): room occupancy is calculated from active
allocation rows rather than stored as a separate counter. The allocation and its capacity effect are
therefore a single row write, performed by one conditional SQL statement that checks capacity and
inserts together.

## TP-13 — Allocation workflow usability (NFR-04)
- Precondition: administrator is trained on the system.
- Action: count the primary data-entry steps after login for a valid allocation.
- Counted steps after login (open the Allocations page is navigation, not data entry):

| # | Step |
|---|---|
| 1 | Choose the student |
| 2 | Choose the room (the list shows only rooms with free capacity) |
| 3 | Press Allocate |

- Expected: no more than five primary data-entry steps.
- Result: 3 steps — Pass. Automated check: `tests/test_nfr04_usability.py`
  (`test_tp13_valid_allocation_needs_at_most_five_data_entry_steps`).
- Also verified: the confirmation names the student and room ("Allocated S101 to room R102"), and
  rejection messages are plain language ("already has an active room allocation", "no available capacity").
- Screenshot: (screenshot of the Allocations page with the form, and of the success message)

## How to reproduce
```bash
python -m pytest tests/test_nfr03_atomicity.py tests/test_nfr04_usability.py -v
python -m pytest -q
```
