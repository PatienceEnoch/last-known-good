# Roadmap

## Phase 1 — Local flight recorder

- [x] Capture routes, interfaces, DNS, failed services, and optional reachability probes
- [x] Compare known-good and current snapshots
- [x] Generate evidence-based Markdown and JSON incident reports
- [x] Test common outage signatures with fixtures

## Phase 2 — Better diagnosis

- [x] Detect address, MTU, latency, and packet-loss changes
- [x] Detect resolver-response changes
- [x] Correlate symptoms into one likely root cause instead of independent alerts
- [ ] Add snapshot redaction and retention controls
- [ ] Add a reproducible Docker-based outage demonstration lab

## Phase 3 — AWS operations layer

- [ ] Provision AWS infrastructure with Terraform
- [ ] Encrypt evidence at rest and in transit
- [ ] Publish redacted health metrics to CloudWatch
- [ ] Store incident summaries and expose a minimal dashboard
- [ ] Add GitHub Actions security and infrastructure checks

## Phase 4 — Guarded recovery

- [ ] Generate an approval-required remediation plan
- [ ] Restrict actions to an explicit allowlist
- [ ] Verify recovery and automatically produce a before/after report
- [ ] Demonstrate rollback when verification fails
