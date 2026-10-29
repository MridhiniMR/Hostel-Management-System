# Bug Fix and Retest Record — BUG-001

## Defect
- Defect ID: BUG-001
- Date: 2026-10-29
- Reporter: Rithvik (found while writing the NFR-03 test, with AI assistance)
- Related requirement: NFR-03 (allocation and capacity update are atomic); FR-06
- Related test case: TP-12

## Original Failure
- Steps: Create a room with capacity 1 and four students. Send four allocation requests for the
  same room at the same moment (automated test `test_nfr03_two_concurrent_requests_cannot_both_take_the_last_bed`).
  The same pattern was used when moving four students into one single-bed room at once
  (`test_nfr03_concurrent_moves_cannot_overfill_a_room`).
- Expected: Exactly one request succeeds. The others are rejected with `ROOM_FULL`.
- Actual: Several requests succeeded. Example run result: `['ok', 'ROOM_FULL', 'ok', 'ok']`
  (3 students allocated to a 1-bed room). The move test failed in 2 of 4 runs
  (e.g. `['ok', 'ok', 'ok', 'ok']`).
- Root cause: The service counted occupants, then inserted/updated in a separate step
  (check-then-act). SQLite ignores the row lock requested with `with_for_update`, so
  concurrent requests all passed the count before any of them wrote.
- Second finding (TP-12): after an unexpected error in the middle of an allocation the service did
  not roll back by itself; the half-written row stayed in the session until the caller closed it
  (`test_tp12_session_is_rolled_back_by_service_on_unexpected_error` failed).
- Screenshot: (attach screenshot of the failing pytest output, if you reproduced it before the fix)

## Diagnosis / AI-Assisted Fix
- Tool: Claude (Anthropic), used as the AI coding assistant
- Prompt/input: Implement NFR-03 tests (forced mid-transaction failure and concurrent last-bed
  allocation) for the Hostel Management System and fix any defect found.
- Suggested change:
  1. `create_allocation`: replace "count, then insert" with a single `INSERT ... SELECT ... WHERE
     active_count < capacity` statement, so the check and the write are one atomic operation.
  2. `update_allocation`: replace "count, then update" with a single conditional `UPDATE`.
  3. Both: `except Exception: db.rollback(); raise` so any unexpected failure undoes the whole transaction.
- Human review: (reviewer name) read the diff in `hms/services.py` and ran the tests locally.
- Patch/commit: (add commit hash / PR link after merge)

## Retest
- Environment: Python 3.13, SQLite (file database for the concurrency tests), pytest
- Steps repeated: `python -m pytest tests/test_nfr03_atomicity.py -q`, run 8 times in a row
- Actual result: all 5 tests passed on every one of the 8 runs (before the fix, the concurrency
  tests failed in most runs). Full suite: 38 passed.
- Pass/Fail: Pass
- Screenshot: (attach screenshot of your own local run of the command above)
- Tester: (your name)
- Date: (date of your local run)

## Regression Check
- Related test cases rerun: full existing suite (`python -m pytest -q`), including FR-04/05/06 tests
- Results: all pass (no regressions)
