"""Keep the reviewed log-product division, figure roles and interval selection."""

import re

from bs4 import BeautifulSoup

from ..word_problems.common import UnsupportedCondition
from .exam_trigonometric_compile import C


def style(parent_html):
    if r"\log_" not in parent_html:
        return None
    soup = BeautifulSoup(parent_html, "html.parser")
    formulas = " ".join(
        n["data-inline-latex"] for n in soup.select("[data-inline-latex]")
    )
    if r"\log_" not in formulas:
        return None
    from .exam_trigonometric_radical_equation import variable_radicals

    if variable_radicals(formulas):
        return None
    text = " ".join(soup.get_text(" ").replace("\xad", "").lower().split())
    method = "inequalities" if re.search(r"двойн\w*\s+неравенств", text) else "circle"
    images = soup.find_all("img")
    if method == "circle" and len(images) not in (1, 2):
        raise UnsupportedCondition(
            "the log-product circle method needs its source figures"
        )
    if method == "inequalities" and len(images) > 1:
        raise UnsupportedCondition(
            "one full-root circle may accompany inequality selection"
        )
    if len(images) == 2:
        parts = [i.find_parent("li") for i in images]
        if any(p is None for p in parts) or [
            p.get("data-list-marker") for p in parts
        ] != ["а)", "б)"]:
            raise UnsupportedCondition(
                "the two log-product figures need separate derivation and selection roles"
            )
    if images:
        position = (
            "before-intro"
            if images[0].find_parent("li")
            else "after-steps"
            if method == "inequalities"
            else "selection"
        )
    else:
        position = "none"
    return C, False, False, position, None, method
