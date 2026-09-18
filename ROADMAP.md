# Network Flight Recorder Roadmap

## Phase 1 — Local Flight Recorder

- [x] Capture routes, interfaces, DNS, failed services, and optional reachability probes
- [x] Compare known-good and current snapshots
- [x] Generate evidence-based Markdown and JSON incident reports
- [x] Test common outage signatures with fixtures

## Phase 2 — Explainable Diagnosis

- [x] Detect address, MTU, latency, and packet-loss changes
- [x] Detect resolver-response changes
- [x] Correlate related symptoms into likely root causes
- [x] Add deterministic snapshot redaction
- [x] Add evidence retention controls
- [x] Add a reproducible Docker-based outage demonstration lab

## Phase 3 — AWS Operations Layer

- [x] Establish Terraform-managed AWS infrastructure
- [x] Create private, versioned S3 evidence storage with SSE-S3 encryption
- [x] Block public access to the evidence bucket
- [x] Enforce encryption in transit
- [x] Upload redacted Network Flight Recorder evidence to S3
- [x] Publish privacy-preserving health metrics to CloudWatch
- [x] Store incident summaries
- [x] Expose a minimal operational dashboard
- [x] Add GitHub Actions application, security, and infrastructure checks

## Phase 4 — Guarded Recovery

- [x] Generate approval-required remediation plans
- [x] Restrict remediation actions to an explicit allowlist
- [x] Add remediation safety guardrails
- [x] Execute an approved remediation in an isolated lab
- [x] Automatically verify whether remediation restored service
- [x] Generate a remediation before-and-after report
- [x] Demonstrate rollback when recovery verification fails

## Phase 5 — Continuous Monitoring

- [x] Add continuous `nfr watch` monitoring
- [x] Compare successive live network snapshots
- [x] Report each monitoring cycle
- [x] Record detected transitions automatically
- [x] Detect both failures and recoveries
- [x] Handle Ctrl+C shutdown cleanly
- [x] Validate watch interval and cycle arguments
- [x] Preserve snapshot history during monitoring
- [x] Add bounded rolling snapshot retention

## Phase 6 — Incident Lifecycle

- [x] Preserve protected before-and-after incident evidence
- [x] Generate automatic incident reports from watch findings
- [x] Link recovery to the original open incident
- [x] Track open and closed incident state
- [x] Recover persisted open incidents after NFR restarts
- [x] Record incident start and recovery timestamps
- [x] Calculate outage duration
- [x] Generate a final failure-to-recovery lifecycle summary
- [ ] Run a complete live failure → recovery watch demonstration
- [ ] Validate multiple sequential incidents in one long-running watch session

## Phase 7 — Final Integration and Validation

- [ ] Run an end-to-end monitored outage in the Docker lab
- [x] Validate failure detection, evidence capture, and recovery in automated tests
- [x] Validate snapshot rotation while protected incident evidence remains intact
- [x] Validate restart recovery during an active incident
- [x] Run the complete automated test suite (69 passed)
- [x] Run Ruff with zero findings
- [x] Validate Terraform formatting and configuration in CI
- [x] Verify GitHub Actions CI passes across Python, security, and Terraform jobs

## Phase 8 — Documentation and Portfolio Release

- [x] Update README with continuous monitoring and incident lifecycle workflow
- [x] Update architecture documentation
- [ ] Add final watch-mode demonstration screenshots
- [x] Document the current CLI commands and examples
- [x] Document safety boundaries and limitations
- [x] Update the validated demonstration records
- [x] Review repository for stale documentation
- [ ] Tag a portfolio-ready release
