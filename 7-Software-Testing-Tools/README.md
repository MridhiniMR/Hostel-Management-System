# Software Testing Tools / Bug Fix / Patch / Retest

The Test Plan requires execution evidence, defect records, security-validation evidence, and final testing results. The supplied test-case document explicitly states that its cases are **Not Executed** until actual execution occurs.

## Required Evidence

For each bug found using a testing tool or AI-assisted/vibe-coding workflow, record:

1. Original failing behavior.
2. Tool/AI used.
3. Prompt or diagnostic input.
4. Suggested fix/patch.
5. Human review.
6. Actual code change/commit.
7. Retest steps.
8. Retest result.
9. Screenshot/evidence.

## Defect Record Template

| Field | Value |
|---|---|
| Defect ID | BUG-XXX |
| Related requirement | FR/NFR/SEC-XX |
| Test case | TP-XX |
| Severity | TODO |
| Original behavior | TODO |
| Expected behavior | TODO |
| Tool used | TODO |
| Fix/patch | TODO |
| Commit/PR | TODO |
| Retest result | TODO |

## Test Execution Status

Do not change `Not Executed` to `Pass`/`Fail` without actual execution evidence.
