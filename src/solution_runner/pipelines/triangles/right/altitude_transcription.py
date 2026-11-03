"""Expose reviewed condition restoration as an explicit local transformation."""

import json
from pathlib import Path

from ...core.condition_transcriptions import transcribe_condition
from .altitude_input import canonical_condition

_DATA = json.loads(Path(__file__).with_name("altitude_transcriptions.json").read_text())
_TRANSCRIPTIONS = {row["condition_sha256"]: row for row in _DATA["entries"]}


def repair_condition(context, parent_asset_id):
    from .planner import _section

    condition = _section(context["normalized_content"], "condition")
    prepared, html = transcribe_condition(
        context,
        condition,
        _TRANSCRIPTIONS,
        validate=lambda copied: canonical_condition(
            _section(copied["normalized_content"], "condition")["html"],
            source=parent_asset_id,
        ),
    )
    if html is None:
        return context, ()
    change = {
        "transformation_target_id": condition["transformation_target_id"],
        "operation": "rewrite",
        "value": {
            "title": "Условие",
            "html": html,
            "asset_keys": list(condition.get("asset_keys", [])),
        },
    }
    return prepared, (change,)
