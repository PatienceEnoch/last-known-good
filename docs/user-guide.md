# Network Flight Recorder User Guide

Network Flight Recorder (NFR) is a local-first Linux network troubleshooting and observability tool. This guide explains how to install it, capture network state, compare healthy and failed conditions, monitor incidents over time, protect sensitive evidence, and run the included Docker demonstrations.

> **New here?** Start with the 5-minute quick start. You do not need AWS or Docker to use NFR's core local diagnostic features.

---

## 1. What NFR does

NFR records a point-in-time view of Linux network state and compares one snapshot with another.

The basic workflow is:

```text
Healthy network
      |
Baseline snapshot
      |
Something changes
      |
Current snapshot
      |
Comparison
      |
Evidence
      |
Likely diagnosis
```

A snapshot can include:

- Routes and default gateway
- Network interfaces
- IPv4 and IPv6 addresses
- DNS resolvers
- Failed systemd services
- Reachability probes
- DNS resolution results
- Latency
- Packet loss
- MTU

Normal collection is local and read-only.

---

## 2. Requirements

For normal local use:

- Linux
- Python 3.10 or newer
- `ip`
- `ping`
- `systemctl` where available
- Git if cloning the repository

Docker is required only for the isolated failure-injection demonstrations.

AWS is optional and is not required for local diagnosis.

---

## 3. Install NFR

Clone the repository:

```bash
git clone https://github.com/PatienceEnoch/network-flight-recorder.git
cd network-flight-recorder
```

Create a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install NFR and its development tools:

```bash
python -m pip install -e ".[dev]"
```

Confirm the CLI is available:

```bash
nfr --help
```

If you open a new terminal later, return to the repository and reactivate the environment:

```bash
cd ~/network-flight-recorder
source .venv/bin/activate
```

---

## 4. Five-minute quick start

### Capture a healthy baseline

Run this while the network is working normally:

```bash
nfr snapshot \
  --probe 1.1.1.1 \
  --dns example.com \
  --output snapshots/baseline.json
```

The baseline is the known-good reference.

### Capture the current state

When a problem appears, capture another snapshot:

```bash
nfr snapshot \
  --probe 1.1.1.1 \
  --dns example.com \
  --output snapshots/current.json
```

### Compare the snapshots

```bash
nfr compare \
  snapshots/baseline.json \
  snapshots/current.json \
  --output reports/incident.md
```

Read the report:

```bash
cat reports/incident.md
```

NFR also records detected findings in the default event log:

```text
events/events.jsonl
```

A report may identify evidence such as:

```text
Default route disappeared
Probe to 1.1.1.1 failed
```

When related findings support a common cause, NFR can produce a correlated diagnosis such as:

```text
Default gateway or routing failure — HIGH confidence
```

The confidence label comes from NFR's diagnostic rules and supporting evidence. It is not a probability.

---

## 5. Understanding snapshots

A snapshot is a JSON record of network state at a specific moment.

Typical files are:

```text
snapshots/baseline.json
snapshots/current.json
```

A snapshot contains sections for the host, network, and system. Network data can include interfaces, addresses, MTU, routes, DNS servers, reachability probes, and DNS probes.

NFR is most useful when the baseline was captured while the system was genuinely healthy.

---

## 6. Use multiple probes

Repeat `--probe` to test more than one destination:

```bash
nfr snapshot \
  --probe 1.1.1.1 \
  --probe 8.8.8.8 \
  --output snapshots/baseline.json
```

Repeat `--dns` to test more than one name:

```bash
nfr snapshot \
  --dns example.com \
  --dns github.com \
  --output snapshots/baseline.json
```

Multiple targets can help distinguish one unreachable service from a broader connectivity problem.

---

## 7. Generate JSON output

Markdown is the default human-readable report format.

For machine-readable output:

```bash
nfr compare \
  snapshots/baseline.json \
  snapshots/current.json \
  --format json \
  --output reports/incident.json
```

---

## 8. Generate a remediation plan

NFR can add a proposed remediation plan to a comparison:

```bash
nfr compare \
  snapshots/baseline.json \
  snapshots/current.json \
  --output reports/incident.md \
  --remediation-plan
```

Generating a plan does **not** automatically change the network.

Remediation is intentionally approval-gated. Current execution is limited to the isolated Docker lab and a tightly scoped default-route restoration action. Generic production remediation is not implemented.

---

## 9. Review the event timeline

NFR records detected findings as events.

The default event log is:

```text
events/events.jsonl
```

View events chronologically:

```bash
nfr timeline
```

Show only recent events:

```bash
nfr timeline --since 1h
```

Supported duration examples include `30m`, `1h`, and `2d`.

You can also filter by event type or source:

```bash
nfr timeline --type routing
nfr timeline --source analyzer
```

To write a timeline to a file:

```bash
nfr timeline --output reports/timeline.md
```

---

## 10. Summarize events

For a compact summary:

```bash
nfr summary
```

For only the last day:

```bash
nfr summary --since 1d
```

A summary includes:

- Total event count
- First observation
- Last observation
- Severity counts
- Event categories

---

## 11. Group events into incidents

View grouped incidents:

```bash
nfr incidents
```

Write them to a report:

```bash
nfr incidents --output reports/incidents.md
```

Events close together in time are grouped so they can be reviewed as one troubleshooting episode rather than unrelated alerts.

---

## 12. Continuous monitoring

Watch mode repeatedly captures network state and compares each new state with the previous one.

Example:

```bash
nfr watch \
  --interval 30 \
  --cycles 10 \
  --probe 1.1.1.1 \
  --dns example.com \
  --snapshot-dir snapshots/watch \
  --snapshot-limit 100
```

`--interval 30` means wait 30 seconds between snapshots.

`--cycles 10` means stop after 10 comparison cycles.

If `--cycles` is omitted, monitoring continues until you stop it with `Ctrl+C`.

For best results, start watch mode while the network is healthy.

---

## 13. Watch-mode evidence

When `--snapshot-dir` is used, the initial state is stored as:

```text
snapshots/watch/0000-baseline.json
```

Later snapshots are numbered:

```text
0001.json
0002.json
0003.json
```

When a failure is detected, protected incident evidence can be stored under:

```text
snapshots/watch/incidents/
```

An incident directory can contain:

```text
before.json
after.json
report.md
status.json
recovery.json
recovery.md
summary.md
```

This preserves evidence from before the failure, during the failure, and after recovery.

---

## 14. Incident lifecycle

A monitored incident can move through this lifecycle:

```text
Healthy
   |
Failure detected
   |
Incident opened
   |
Evidence preserved
   |
Recovery detected
   |
Incident closed
   |
Lifecycle summary written
```

The completed incident record can include:

- Incident start time
- Recovery time
- Outage duration
- Failure evidence
- Recovery evidence

NFR can also recover a persisted open incident after a monitoring restart.

---

## 15. Redact sensitive information

Network snapshots can contain infrastructure details such as hostnames and IP addresses.

NFR supports deterministic pseudonymization.

Set a private redaction key:

```bash
export NFR_REDACTION_KEY="use-a-long-private-value"
```

Then capture a protected snapshot:

```bash
nfr snapshot \
  --redact \
  --probe 1.1.1.1 \
  --dns example.com \
  --output snapshots/shared.json
```

Use the same redaction key for snapshots that need to remain comparable.

Do not commit the redaction key to Git.

---

## 16. Snapshot retention

Preview snapshots that would be removed:

```bash
nfr prune \
  --directory snapshots \
  --keep 100 \
  --max-age-days 30
```

This is a dry run. Nothing is deleted.

After reviewing the list, apply cleanup explicitly:

```bash
nfr prune \
  --directory snapshots \
  --keep 100 \
  --max-age-days 30 \
  --apply
```

The separate `--apply` step protects against accidental deletion.

---

## 17. Docker outage demonstration

The repository includes an isolated Docker failure-injection lab.

Requirements:

- Docker Engine or Docker Desktop
- Docker Compose v2
- Internet access during the first image build

Run:

```bash
./lab/run_demo.sh
```

The demonstration:

1. Starts an isolated container.
2. Captures a healthy baseline.
3. Removes the container's default route.
4. Captures the failed state.
5. Compares the two snapshots.
6. Diagnoses the routing failure.
7. Writes an incident report.
8. Restores the disposable Docker environment.

The injected failure occurs inside the container, not on the host network.

---

## 18. Guarded recovery demonstration

Run:

```bash
./lab/run_guarded_recovery.sh
```

The control flow is:

```text
Observe
   |
Diagnose
   |
Propose
   |
Approve
   |
Execute
   |
Verify
```

The demonstration writes before-and-after evidence to:

```text
reports/remediation.md
```

---

## 19. Rollback demonstration

Run:

```bash
./lab/run_rollback_demo.sh
```

This intentionally forces post-remediation verification to fail. NFR then exercises its rollback path and restores the pre-remediation route state.

The purpose is to demonstrate that failed verification does not leave the isolated lab in an unverified changed state.

---

## 20. Watch demonstrations

Single outage and recovery:

```bash
./lab/run_watch_recovery_demo.sh
```

Multiple sequential incidents:

```bash
./lab/run_multi_incident_demo.sh
```

These demonstrations exercise:

- Failure detection
- Recovery detection
- Incident opening
- Incident closure
- Protected evidence
- Outage duration
- Multiple incidents in one continuous watch session

---

## 21. Docker safety boundaries

The Docker demonstrations intentionally alter network state, but failure injection is isolated.

Important boundaries:

- `NET_ADMIN` is granted to the container, not the host.
- Docker host networking is not used.
- Failure injection changes container network state only.
- Cleanup restores the disposable environment.
- Normal collection and diagnosis remain read-only.
- Remediation cannot execute arbitrary shell commands.
- Generic production remediation and rollback are not implemented.

Only run failure-injection demonstrations on systems you own or are authorized to administer.

---

## 22. Optional AWS integration

AWS is not required for local diagnosis.

The AWS operations layer includes Terraform-managed infrastructure for:

- Private S3 evidence storage
- S3 versioning
- Encryption
- Public-access blocking
- CloudWatch health metrics
- CloudWatch incident summaries
- Operational dashboarding

Infrastructure is defined under:

```text
infra/aws/
```

Publish snapshot health metrics with:

```bash
nfr snapshot \
  --probe 1.1.1.1 \
  --output snapshots/current.json \
  --cloudwatch
```

Publish an incident summary during comparison:

```bash
nfr compare \
  snapshots/baseline.json \
  snapshots/current.json \
  --cloudwatch
```

These features require the AWS CLI to be installed and authenticated with the required permissions.

The current CLI CloudWatch implementation uses `us-east-1`.

Core collection and diagnosis continue to work without AWS.

---

## 23. Help commands

Show all commands:

```bash
nfr --help
```

Show help for an individual command:

```bash
nfr snapshot --help
nfr compare --help
nfr watch --help
nfr timeline --help
nfr summary --help
nfr incidents --help
nfr prune --help
```

---

## 24. Common problems

### `nfr: command not found`

Activate the virtual environment:

```bash
source .venv/bin/activate
```

If necessary, reinstall the project:

```bash
python -m pip install -e ".[dev]"
```

### Some network information is missing

NFR collects information defensively. If utilities such as `ip`, `ping`, or `systemctl` are unavailable, portions of a snapshot may be empty rather than causing the entire snapshot to fail.

### A probe fails but the network still seems usable

One failed probe does not prove that the entire network is down.

Review the surrounding evidence:

- Default route
- Interface state
- DNS
- Other probes
- Packet loss
- Latency

NFR is designed to correlate multiple signals.

### A Docker demonstration will not start

Check Docker:

```bash
docker --version
docker compose version
```

Validate the Compose configuration:

```bash
docker compose config
```

### CloudWatch publishing fails

Confirm AWS authentication:

```bash
aws sts get-caller-identity
```

Then verify that the expected AWS resources and permissions are configured.

---

## 25. Practical troubleshooting workflow

A useful operating workflow is:

```text
1. Capture a healthy baseline.
2. Keep it available locally.
3. When a problem appears, capture the current state.
4. Compare the snapshots.
5. Read the evidence before changing anything.
6. Verify the likely cause.
7. Make an authorized correction.
8. Capture another snapshot.
9. Confirm recovery.
10. Preserve important incident evidence.
```

The central principle is:

> Preserve the evidence needed to explain a failure before changing the system.

---

## Additional documentation

- [CLI reference](cli-reference.md)
- [Architecture](architecture.md)
- [Docker lab](docker-lab.md)
- [Validation status](validation-status.md)
