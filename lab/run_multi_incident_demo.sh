#!/usr/bin/env sh
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$project_dir"

restore_lab() {
    docker compose restart recorder >/dev/null 2>&1 || true
}

trap restore_lab EXIT INT TERM

echo "Starting NFR multiple-incident watch lab..."
docker compose up --build --detach

rm -rf snapshots/multi-watch-demo
rm -f reports/multi-watch-events.jsonl
rm -f reports/multi-watch-output.txt

gateway=$(
    docker compose exec -T recorder sh -c \
        "ip route show default | awk 'NR==1 {print \$3}'"
)

interface=$(
    docker compose exec -T recorder sh -c \
        "ip route show default | awk 'NR==1 {print \$5}'"
)

echo "Known-good route: $gateway via $interface"

docker compose exec -T recorder nfr watch \
    --interval 2 \
    --cycles 6 \
    --probe 1.1.1.1 \
    --log reports/multi-watch-events.jsonl \
    --snapshot-dir snapshots/multi-watch-demo \
    --snapshot-limit 20 \
    > reports/multi-watch-output.txt 2>&1 &

watch_pid=$!

echo "Waiting for baseline..."
while [ ! -f snapshots/multi-watch-demo/0000-baseline.json ]; do
    sleep 1
done

echo "1. Injecting first outage..."
docker compose exec -T recorder ip route del default

while ! grep -R -q '"status": "open"' \
    snapshots/multi-watch-demo/incidents 2>/dev/null; do
    sleep 1
done

echo "First incident opened."

echo "2. Restoring first outage..."
docker compose exec -T recorder \
    ip route replace default via "$gateway" dev "$interface"

while ! grep -R -q '"status": "closed"' \
    snapshots/multi-watch-demo/incidents 2>/dev/null; do
    sleep 1
done

echo "First incident closed."

echo "3. Injecting second outage..."
docker compose exec -T recorder ip route del default

while [ "$(find snapshots/multi-watch-demo/incidents \
    -name status.json \
    -exec grep -l '"status": "open"' {} \; \
    2>/dev/null | wc -l)" -lt 1 ]; do
    sleep 1
done

echo "Second incident opened."

echo "4. Restoring second outage..."
docker compose exec -T recorder \
    ip route replace default via "$gateway" dev "$interface"

wait "$watch_pid"

echo
echo "Watch output:"
cat reports/multi-watch-output.txt

incident_count=$(
    find snapshots/multi-watch-demo/incidents \
        -name status.json \
        -type f \
        | wc -l
)

closed_count=$(
    grep -R -l '"status": "closed"' \
        snapshots/multi-watch-demo/incidents/*/status.json \
        2>/dev/null \
        | wc -l
)

echo
echo "Incidents recorded: $incident_count"
echo "Incidents closed: $closed_count"

if [ "$incident_count" -ne 2 ]; then
    echo "Expected exactly 2 incidents."
    exit 1
fi

if [ "$closed_count" -ne 2 ]; then
    echo "Expected both incidents to close."
    exit 1
fi

echo
echo "Incident summaries:"
for summary in snapshots/multi-watch-demo/incidents/*/summary.md; do
    echo
    echo "===== $summary ====="
    cat "$summary"
done

echo
echo "Multiple sequential incident demonstration completed successfully."

restore_lab
trap - EXIT INT TERM
