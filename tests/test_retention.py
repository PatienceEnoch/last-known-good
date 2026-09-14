from datetime import datetime, timezone
from os import utime

from network_flight_recorder.retention import apply_prune, prune_candidates


def test_retention_is_dry_run_until_candidates_are_applied(tmp_path):
    now = datetime(2026, 9, 14, tzinfo=timezone.utc)
    files = []
    for index, age_days in enumerate((1, 2, 40)):
        path = tmp_path / f"snapshot-{index}.json"
        path.write_text("{}", encoding="utf-8")
        timestamp = now.timestamp() - age_days * 86400
        utime(path, (timestamp, timestamp))
        files.append(path)
    ignored = tmp_path / "notes.txt"
    ignored.write_text("keep", encoding="utf-8")

    candidates = prune_candidates(tmp_path, keep=2, max_age_days=30, now=now)
    assert candidates == [files[2]]
    assert all(path.exists() for path in files)

    assert apply_prune(candidates) == 1
    assert not files[2].exists()
    assert ignored.exists()
