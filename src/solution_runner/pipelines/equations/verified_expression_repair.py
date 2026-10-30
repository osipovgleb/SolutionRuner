"""Replay reviewed source transcriptions only for the exact damaged question."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

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


def repair_verified_condition(context):
    content = _normalized_content(context)
    condition = _section(content, "condition")
    if condition is None:
        return context, None
    html = condition.get("html", "")
    if not isinstance(html, str):
        raise UnsupportedCondition("a canonical condition HTML string is required")
    digest = hashlib.sha256(html.encode()).hexdigest()
    row = _TRANSCRIPTIONS.get(digest)
    if row is None or html != row["before_html"]:
        return context, None
    read_math_markup(context)
    copied = deepcopy(context)
    fixed = _section(copied["normalized_content"], "condition")
    fixed["html"] = row["after_html"]
    change = _section_transformation(condition, "condition", "Условие", fixed["html"])
    return copied, change
