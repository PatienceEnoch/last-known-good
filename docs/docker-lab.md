# Disposable outage lab

The lab creates a dedicated Docker bridge network, records healthy state, deletes the default
route **inside the recorder container**, captures the failed state, and generates an incident
report. Restarting the container restores its Docker-managed network configuration.

## Requirements

- Docker Engine or Docker Desktop with Compose v2
- Internet access during the first image build

## Run

```bash
./lab/run_demo.sh
```

The resulting evidence is written to `snapshots/` and `reports/incident.md`. When finished:

```bash
docker compose down
```

## Safety boundaries

- The container receives `NET_ADMIN`; the host does not.
- The lab uses Docker's isolated bridge and does not use host networking.
- The script changes only the container's default route.
- A cleanup trap restarts the container if the demonstration exits early.
- Network Flight Recorder itself remains read-only.

Run failure-injection demonstrations only on systems you own or are authorized to administer.
