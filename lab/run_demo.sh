#!/usr/bin/env sh
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$project_dir"

restore_lab() {
    docker compose restart recorder >/dev/null 2>&1 || true
}
trap restore_lab EXIT INT TERM

docker compose up --build --detach

echo "Capturing healthy baseline..."
docker compose exec -T recorder nfr snapshot \
    --probe 1.1.1.1 --dns example.com --output snapshots/baseline.json

echo "Injecting an isolated default-route failure inside the lab container..."
docker compose exec -T recorder ip route del default

echo "Capturing failed state and reconstructing the incident..."
docker compose exec -T recorder nfr snapshot \
    --probe 1.1.1.1 --dns example.com --output snapshots/current.json
docker compose exec -T recorder nfr compare \
    snapshots/baseline.json snapshots/current.json --output reports/incident.md

echo "Incident report: reports/incident.md"
cat reports/incident.md

restore_lab
trap - EXIT INT TERM
