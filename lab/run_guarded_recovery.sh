#!/usr/bin/env sh
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$project_dir"

restore_lab() {
    docker compose restart recorder >/dev/null 2>&1 || true
}

trap restore_lab EXIT INT TERM

echo "Starting isolated NFR Docker lab..."
docker compose up --build --detach

echo "1. Capturing known-good baseline..."
docker compose exec -T recorder nfr snapshot \
    --probe 1.1.1.1 \
    --dns example.com \
    --output snapshots/remediation-baseline.json

echo "2. Injecting default-route failure INSIDE container..."
docker compose exec -T recorder ip route del default

echo "3. Capturing failed network state..."
docker compose exec -T recorder nfr snapshot \
    --probe 1.1.1.1 \
    --dns example.com \
    --output snapshots/remediation-failed.json

echo "4. Diagnosing failure and executing approved remediation..."
docker compose exec -T recorder python - <<'PY'
import json
from pathlib import Path

from network_flight_recorder.analyzer import analyze, diagnose
from network_flight_recorder.lab_remediation import execute_lab_remediation
from network_flight_recorder.remediation import (
    execute_remediation,
    generate_remediation_plan,
)

baseline = json.loads(
    Path("snapshots/remediation-baseline.json").read_text(
        encoding="utf-8"
    )
)

failed = json.loads(
    Path("snapshots/remediation-failed.json").read_text(
        encoding="utf-8"
    )
)

findings = analyze(baseline, failed)
diagnosis = diagnose(findings)
plan = generate_remediation_plan(diagnosis)

if plan is None:
    raise RuntimeError("NFR could not generate a remediation plan")

print(f"Diagnosis: {plan.diagnosis}")
print(f"Action: {plan.action_id}")
print("Approval: YES")

execute_remediation(
    plan,
    approved=True,
    executor=lambda action_id: execute_lab_remediation(
        action_id,
        baseline,
    ),
)

print("Remediation command executed.")
PY

echo "5. Capturing post-remediation state..."
docker compose exec -T recorder nfr snapshot \
    --probe 1.1.1.1 \
    --dns example.com \
    --output snapshots/remediation-recovered.json

echo "6. Verifying recovery..."
docker compose exec -T recorder python - <<'PY'
import json
from pathlib import Path

from network_flight_recorder.lab_remediation import (
    verify_lab_remediation,
)

baseline = json.loads(
    Path("snapshots/remediation-baseline.json").read_text(
        encoding="utf-8"
    )
)

recovered = json.loads(
    Path("snapshots/remediation-recovered.json").read_text(
        encoding="utf-8"
    )
)

verified = verify_lab_remediation(
    "renew_network_configuration",
    baseline,
    recovered,
)

if not verified:
    raise RuntimeError("Remediation verification FAILED")

print("Recovery verification: PASSED")
PY

echo "Guarded recovery demonstration completed successfully."

restore_lab
trap - EXIT INT TERM
