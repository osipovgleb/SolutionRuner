"""Write progress checkpoints for polygon asset runs."""

from __future__ import annotations

from datetime import UTC, datetime

if __package__:
    from .mcp_polygon_util import _atomic_write_json
else:
    from mcp_polygon_util import _atomic_write_json


def write_progress(run_dir, args, theme, group, counts, totals):
    """Persist the latest completed batch and cumulative outcome counts."""
    batches_seen, tasks_seen = counts
    _atomic_write_json(
        run_dir / "progress.json",
        {
            "at": datetime.now(UTC).isoformat(),
            "mode": args.mode,
            "last_theme": theme.title,
            "last_source_group_id": group.source_group_id,
            "last_group_key": group.group_key,
            "batches_seen": batches_seen,
            "tasks_seen": tasks_seen,
            "totals": dict(sorted(totals.items())),
        },
    )
