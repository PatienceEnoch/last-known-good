# Disposable outage and guarded-recovery lab

The lab creates a dedicated Docker bridge network and changes network state only inside the
recorder container. Two scripts demonstrate different parts of the system.

## Requirements

- Docker Engine or Docker Desktop with Compose v2
- Internet access during the first image build

## Diagnostic demonstration

```bash
./lab/run_demo.sh
```

The resulting evidence is written to `snapshots/` and `reports/incident.md`. When finished:

```bash
docker compose down
```

## Guarded-recovery demonstration

```bash
./lab/run_guarded_recovery.sh
```

This workflow:

1. Captures a known-good baseline.
2. Removes the container's default route.
3. Diagnoses the failure.
4. Generates an approval-required remediation plan.
5. Executes the allowlisted lab action with explicit approval.
6. Captures a post-change snapshot.
7. Verifies the expected gateway and interface.
8. Writes `reports/remediation.md` with before-and-after evidence.

## Safety boundaries

- The container receives `NET_ADMIN`; the host does not.
- The lab uses Docker's isolated bridge and does not use host networking.
- The script changes only the container's default route.
- A cleanup trap restarts the container if the demonstration exits early.
- Normal collection and diagnosis remain read-only.
- Remediation execution exists only in the guarded-recovery lab, accepts no arbitrary shell
  command, and currently supports one exact default-route restoration action.
- Automatic rollback after failed verification is not implemented.

Run failure-injection demonstrations only on systems you own or are authorized to administer.
