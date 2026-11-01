"""Keep the reviewed log-product division, figure roles and interval selection."""

import re

from bs4 import BeautifulSoup

from ..word_problems.common import UnsupportedCondition
from .exam_trigonometric_compile import C


def style(parent_html, condition=""):
    if r"\log_" not in (parent_html + condition):
        return None
    soup = BeautifulSoup(parent_html, "html.parser")
    formulas = " ".join(
        n["data-inline-latex"] for n in soup.select("[data-inline-latex]")
    )
    if r"\log_" not in formulas + condition:
        return None
    from .exam_trigonometric_radical_equation import variable_radicals

    if variable_radicals(condition or formulas):
        return None
    text = " ".join(soup.get_text(" ").replace("\xad", "").lower().split())
    text = text.split("примечание")[0]
    method = (
        "inequalities"
        if re.search(r"двойн\w*\s+неравенств|решим неравенства", text)
        else "circle"
    )
    images = soup.find_all("img")
    if "другое решение пункта б" in text:
        if len(images) != 2 or "числовой оси" not in text or "окружност" not in text:
            raise UnsupportedCondition(
                "both reviewed interval selection methods are required"
            )
        return C, False, False, "selection", None, "log_dual_selection"
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
        ] not in (["а)", "б)"], ["а)", "а)"]):
            raise UnsupportedCondition(
                "the two log-product figures need separate derivation and selection roles"
            )
    if images:
        position = (
            (
                "after-intro"
                if any(str(n).strip() for n in images[0].previous_siblings)
                else "before-intro"
            )
            if images[0].find_parent("li")
            else "after-steps"
            if method == "inequalities"
            else "selection"
        )
    else:
        position = "none"
    return C, False, False, position, None, method
