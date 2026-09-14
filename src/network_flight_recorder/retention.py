"""Plan safe cleanup of locally stored JSON snapshots."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path


def prune_candidates(
    directory: Path, keep: int = 100, max_age_days: int = 30, now: datetime | None = None
) -> list[Path]:
    """Return snapshot files exceeding either count or age limits, oldest first."""
    if keep < 1 or max_age_days < 1:
        raise ValueError("keep and max_age_days must both be at least 1")
    if not directory.exists():
        return []
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=max_age_days)
    files = sorted(directory.glob("*.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    candidates: set[Path] = set(files[keep:])
    for path in files:
        modified = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        if modified < cutoff:
            candidates.add(path)
    return sorted(candidates, key=lambda path: path.stat().st_mtime)


def apply_prune(candidates: list[Path]) -> int:
    """Delete only the explicitly planned files and return the count removed."""
    for path in candidates:
        path.unlink()
    return len(candidates)
