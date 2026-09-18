# CLI reference

Install the project in an isolated Python environment before using these
commands:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

## Capture a snapshot

```bash
nfr snapshot \
  --probe 1.1.1.1 \
  --dns example.com \
  --output snapshots/baseline.json
```

Repeat `--probe` or `--dns` to collect multiple targets. Add `--redact` to
pseudonymize sensitive fields before writing, or `--cloudwatch` to publish
privacy-preserving health metrics.

## Compare two snapshots

```bash
nfr compare \
  snapshots/baseline.json \
  snapshots/current.json \
  --output reports/incident.md \
  --remediation-plan
```

Use `--format json` for machine-readable output. `--cloudwatch` publishes a
privacy-preserving incident summary to CloudWatch Logs. A generated remediation
plan requires approval and does not execute by itself.

## Monitor continuously

```bash
nfr watch \
  --interval 30 \
  --cycles 10 \
  --probe 1.1.1.1 \
  --dns example.com \
  --log reports/events.jsonl \
  --snapshot-dir snapshots/watch \
  --snapshot-limit 100
```

Omit `--cycles` for an open-ended session and stop it with Ctrl+C. The interval
and cycle count must be positive. The snapshot limit bounds ordinary watch
history while incident evidence is stored separately.

## Inspect recorded events

```bash
nfr timeline --log reports/events.jsonl --since 1h
nfr summary --log reports/events.jsonl --since 1d
nfr incidents --log reports/events.jsonl --output reports/incidents.md
```

Each command can filter by `--type`, `--source`, or a recent duration such as
`30m`, `1h`, or `2d`.

## Plan or apply retention

Preview cleanup without deleting anything:

```bash
nfr prune --directory snapshots --keep 100 --max-age-days 30
```

Apply the displayed plan only after review:

```bash
nfr prune \
  --directory snapshots \
  --keep 100 \
  --max-age-days 30 \
  --apply
```

## Run the Docker demonstrations

```bash
./lab/run_demo.sh
./lab/run_guarded_recovery.sh
./lab/run_rollback_demo.sh
./lab/run_watch_recovery_demo.sh
```

All demonstrations change network state only inside the disposable recorder
container. See [Docker lab safety boundaries](docker-lab.md) before running
them.
