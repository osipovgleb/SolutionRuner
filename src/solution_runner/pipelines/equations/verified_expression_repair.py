"""Replay reviewed source transcriptions only for the exact damaged question."""

import json
from pathlib import Path

from ..core.condition_transcriptions import transcribe_condition
from ..probability.common import UnsupportedCondition
from ..triangles.isosceles.planner import (
    _normalized_content,
    _section,
    _section_transformation,
)
from .expression_condition import read_math_markup

_DATA = json.loads(
    Path(__file__).with_name("verified_expression_transcriptions.json").read_text()
)
_TRANSCRIPTIONS = {row["condition_sha256"]: row for row in _DATA["entries"]}


def repair_verified_condition(context, *, validate=read_math_markup):
    content = _normalized_content(context)
    condition = _section(content, "condition")
    if condition is None:
        return context, None
    html = condition.get("html", "")
    if not isinstance(html, str):
        raise UnsupportedCondition("a canonical condition HTML string is required")
    prepared, repaired_html = transcribe_condition(
        context, condition, _TRANSCRIPTIONS, validate=validate
    )
    if repaired_html is None:
        return context, None
    change = _section_transformation(condition, "condition", "Условие", repaired_html)
    return prepared, change
