#!/usr/bin/env sh
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$project_dir"

restore_lab() {
    docker compose restart recorder >/dev/null 2>&1 || true
}

trap restore_lab EXIT INT TERM

echo "Starting isolated NFR rollback lab..."
docker compose up --build --detach

echo "1. Capturing known-good baseline..."
docker compose exec -T recorder nfr snapshot \
    --probe 1.1.1.1 \
    --dns example.com \
    --output snapshots/rollback-baseline.json

echo "2. Injecting default-route failure INSIDE container..."
docker compose exec -T recorder ip route del default

echo "3. Capturing failed state..."
docker compose exec -T recorder nfr snapshot \
    --output snapshots/rollback-before.json

echo "4. Running remediation with forced verification failure..."
docker compose exec -T recorder python - <<'PY'
import json
import subprocess
from pathlib import Path

from network_flight_recorder.lab_remediation import (
    execute_lab_remediation,
    remediate_with_rollback,
)

baseline = json.loads(
    Path("snapshots/rollback-baseline.json").read_text(
        encoding="utf-8"
    )
)

calls = []


def remediate():
    calls.append("remediate")
    execute_lab_remediation(
        "renew_network_configuration",
        baseline,
    )


def verify():
    calls.append("verify")

    # This demo deliberately simulates failed post-change verification
    # so the rollback path can be exercised safely and deterministically.
    return False


def rollback():
    calls.append("rollback")
    subprocess.run(
        ["ip", "route", "del", "default"],
        check=True,
    )


result = remediate_with_rollback(
    remediate=remediate,
    verify=verify,
    rollback=rollback,
)

if result:
    raise RuntimeError(
        "Rollback demonstration unexpectedly reported success"
    )

if calls != ["remediate", "verify", "rollback"]:
    raise RuntimeError(
        f"Unexpected execution order: {calls}"
    )

print("Verification: FAILED as expected")
print("Rollback: EXECUTED")
print(f"Execution order: {calls}")
PY

echo "5. Capturing post-rollback state..."
docker compose exec -T recorder nfr snapshot \
    --output snapshots/rollback-after.json

echo "Rollback demonstration completed successfully."

restore_lab
trap - EXIT INT TERM
