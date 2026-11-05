"""Restore the reviewed full-immersion qualifier visibly in the prepared condition."""

import hashlib
import re

from ..core.errors import ContentPlanError
from ..word_problems.common import rewrite
from .prism_sources import DATA


def clarified(html):
    if not isinstance(html, str):
        raise ContentPlanError("complete prism condition HTML is required")
    digest = hashlib.sha256(html.encode()).hexdigest()
    record = DATA["water_transcriptions"].get(digest)
    if record is None:
        return html
    result, count = re.subn(
        "по\xad?гру\xad?зи\xad?ли", lambda m: "полностью " + m[0], html
    )
    if (
        count != 1
        or hashlib.sha256(result.encode()).hexdigest() != record["corrected_sha256"]
    ):
        raise ContentPlanError("the reviewed prism immersion transcription changed")
    return result


def correction(condition):
    html = clarified(condition["html"])
    if html == condition["html"]:
        return ()
    change = rewrite(condition, "condition", condition.get("title", "Условие"), html)
    change["value"]["asset_keys"] = condition["asset_keys"]
    return (change,)
