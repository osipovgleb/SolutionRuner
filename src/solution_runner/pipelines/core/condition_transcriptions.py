"""Copy an exact reviewed source transcription before deterministic planning."""

import hashlib
from copy import deepcopy

from .errors import ContentPlanError


def transcribe_condition(context, condition, transcriptions, *, validate):
    html = condition.get("html", "")
    if not isinstance(html, str):
        raise ContentPlanError("a canonical condition HTML string is required")
    row = transcriptions.get(hashlib.sha256(html.encode()).hexdigest())
    if row is None or html != row["before_html"]:
        return context, None
    index = context["normalized_content"]["sections"].index(condition)
    copied = deepcopy(context)
    copied["normalized_content"]["sections"][index]["html"] = row["after_html"]
    validate(copied)
    return copied, row["after_html"]
