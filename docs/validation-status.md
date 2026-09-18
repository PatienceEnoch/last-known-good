# Current validation status

This record separates what has been implemented and tested from what still
requires a live demonstration.

## Validation date and revision

- Date: September 18, 2026 (UTC)
- Revision reviewed: `8329216`
- Environment for local Python checks: clean repository checkout, Python 3.12

## Automated application validation

Commands:

```bash
pytest -q
ruff check .
```

Results:

- 69 tests passed
- Ruff completed with zero findings

The automated suite covers snapshot analysis, diagnosis, privacy controls,
retention, event recording, incident grouping, CloudWatch command generation,
remediation approval and allowlisting, lab recovery verification, watch-mode
transitions, bounded snapshot history, protected incident evidence, persisted
incident recovery after restart, outage duration, and lifecycle summaries.

## Guarded-recovery validation

The isolated Docker recovery workflow completed successfully with:

- Before remediation: default route missing
- Known-good route: `172.18.0.1` via `eth0`
- After remediation: `172.18.0.1` via `eth0`
- Verification: passed
- Generated evidence: `reports/remediation.md`

This validates the implemented control path:

```text
failure → diagnosis → approval-required plan → allowlist check →
lab execution → post-change snapshot → verification → report
```

## GitHub Actions validation

The `CI and Security` workflow for revision `8329216` completed successfully in
[run 35376936422](https://github.com/PatienceEnoch/network-flight-recorder/actions/runs/35376936422).

All three jobs passed:

- Python tests and Ruff linting
- Python dependency security audit
- Terraform formatting, initialization, and validation

## Validation still outstanding

The following items are intentionally not claimed as complete:

- Multiple sequential live incidents in one long-running watch session
- Final watch-mode screenshots and a portfolio release tag

The earlier 11-test milestone remains available in the
[historical Phase 2 validation record](validated-demo.md).
