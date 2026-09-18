# Disposable outage and guarded-recovery lab

The lab uses a dedicated Docker bridge and changes network state only inside the recorder container. It is designed for failure injection without touching the host network.

## Requirements

- Docker Engine or Docker Desktop with Compose v2
- Internet access during the first image build

## Diagnostic demonstration

```bash
./lab/run_demo.sh
```

This path captures a healthy baseline, removes the container's default route, records the failed state, diagnoses the outage, and writes evidence to `snapshots/` and `reports/incident.md`.

When finished:

```bash
docker compose down
```

## Guarded-recovery demonstration

```bash
./lab/run_guarded_recovery.sh
```

The workflow:

1. Captures a known-good baseline.
2. Removes the container's default route.
3. Diagnoses the failure.
4. Generates an approval-required remediation plan.
5. Executes the allowlisted lab action with explicit approval.
6. Captures a post-change snapshot.
7. Verifies the expected gateway and interface.
8. Writes `reports/remediation.md` with before-and-after evidence.

## Rollback demonstration

```bash
./lab/run_rollback_demo.sh
```

This demonstration exercises the failure path. It runs the guarded remediation flow, forces post-change verification to fail, and then restores the pre-remediation route state through the rollback path.

The point is not to simulate a general self-healing network. It is to prove that a failed verification does not leave the lab in an unverified changed state.

## Watch and incident-lifecycle demonstrations

```bash
./lab/run_watch_recovery_demo.sh
./lab/run_multi_incident_demo.sh
```

These scripts exercise failure/recovery transition detection, incident closure, protected evidence, lifecycle summaries, and multiple sequential incidents in a continuous watch session.

## Safety boundaries

- `NET_ADMIN` is granted to the container, not the host.
- The lab uses Docker's isolated bridge and does not use host networking.
- Failure injection changes only the container's network state.
- Cleanup logic restores the disposable environment if a demonstration exits early.
- Normal collection and diagnosis remain read-only.
- Remediation accepts no arbitrary shell command and currently supports one exact default-route restoration action.
- Rollback is implemented only for the isolated lab path; generic production remediation and rollback are not implemented.

Run failure-injection demonstrations only on systems you own or are authorized to administer.
