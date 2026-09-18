#!/usr/bin/env sh
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$project_dir"

restore_lab() {
    docker compose restart recorder >/dev/null 2>&1 || true
}

trap restore_lab EXIT INT TERM

echo "Starting isolated NFR watch recovery lab..."
docker compose up --build --detach

rm -rf snapshots/watch-demo
rm -f reports/watch-demo-events.jsonl
rm -f reports/watch-demo-output.txt

gateway=$(
    docker compose exec -T recorder sh -c \
        "ip route show default | awk 'NR==1 {print \$3}'"
)

interface=$(
    docker compose exec -T recorder sh -c \
        "ip route show default | awk 'NR==1 {print \$5}'"
)

if [ -z "$gateway" ] || [ -z "$interface" ]; then
    echo "Could not determine the known-good default route."
    exit 1
fi

echo "Known-good route: $gateway via $interface"

echo "1. Starting live NFR watch session..."
docker compose exec -T recorder nfr watch \
    --interval 2 \
    --cycles 3 \
    --probe 1.1.1.1 \
    --log reports/watch-demo-events.jsonl \
    --snapshot-dir snapshots/watch-demo \
    --snapshot-limit 20 \
    > reports/watch-demo-output.txt 2>&1 &

watch_pid=$!

echo "2. Waiting for watch baseline..."
count=0

while [ ! -f snapshots/watch-demo/0000-baseline.json ]; do
    if ! kill -0 "$watch_pid" 2>/dev/null; then
        echo "Watch process stopped unexpectedly."
        cat reports/watch-demo-output.txt
        exit 1
    fi

    count=$((count + 1))

    if [ "$count" -gt 60 ]; then
        echo "Timed out waiting for watch baseline."
        exit 1
    fi

    sleep 1
done

echo "Baseline captured."

echo "3. Injecting default-route failure INSIDE container..."
docker compose exec -T recorder ip route del default

echo "4. Waiting for NFR to open an incident..."
count=0
status_file=""

while [ -z "$status_file" ]; do
    if ! kill -0 "$watch_pid" 2>/dev/null; then
        echo "Watch process stopped before opening an incident."
        cat reports/watch-demo-output.txt
        exit 1
    fi

    status_file=$(
        find snapshots/watch-demo/incidents \
            -type f \
            -name status.json \
            2>/dev/null \
            | head -n 1 \
            || true
    )

    if [ -n "$status_file" ]; then
        if ! grep -q '"status": "open"' "$status_file"; then
            status_file=""
        fi
    fi

    count=$((count + 1))

    if [ "$count" -gt 60 ]; then
        echo "Timed out waiting for incident detection."
        exit 1
    fi

    sleep 1
done

echo "Incident opened: $status_file"

echo "5. Restoring known-good default route..."
docker compose exec -T recorder \
    ip route replace default via "$gateway" dev "$interface"

echo "6. Waiting for NFR to detect recovery..."
wait "$watch_pid"

echo
echo "Watch output:"
cat reports/watch-demo-output.txt

if ! grep -q '"status": "closed"' "$status_file"; then
    echo "Incident did not close after recovery."
    cat "$status_file"
    exit 1
fi

incident_dir=$(dirname "$status_file")

if [ ! -f "$incident_dir/summary.md" ]; then
    echo "Lifecycle summary was not generated."
    exit 1
fi

echo
echo "Final incident status:"
cat "$status_file"

echo
echo "Lifecycle summary:"
cat "$incident_dir/summary.md"

echo
echo "Live failure-to-recovery watch demonstration completed successfully."

restore_lab
trap - EXIT INT TERM
