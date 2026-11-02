"""Read the original log identity, substitution and intermediate figure stage."""

import re

from bs4 import BeautifulSoup

from ..word_problems.common import UnsupportedCondition
from .exam_trigonometric_compile import C, S
from .power_arithmetic import clean


def parent_kind(parent_html):
    soup = BeautifulSoup(parent_html, "html.parser")
    forms = [clean(n["data-inline-latex"]) for n in soup.select("[data-inline-latex]")]
    text = " ".join(soup.get_text(" ").replace("\xad", "").lower().split())
    if any(
        s in text
        for s in (
            "другое решение",
            "ещё одно решение",
            "еще одно решение",
            "изложим решение",
            "другим способом",
        )
    ):
        raise UnsupportedCondition(
            "an additional logarithm identity method needs review"
        )
    direct = (
        "chain"
        if r"\log_ab\cdot\log_bc=\log_ac" in forms and "тождество" in text
        else "power"
        if "правая часть" in text and "логарифма равна" in text
        else None
    )
    if direct:
        if any(re.search(r"(?<![A-Za-z])[tyuzv]=", f) for f in forms):
            raise UnsupportedCondition(
                "the direct log identity must not discard another substitution"
            )
        return direct, ""
    from .exam_trigonometric_log_base_change_style import finite_kind
    from .exam_trigonometric_log_base_change_style import kind as base_change

    algebraic = base_change(forms) or finite_kind(forms)
    if algebraic is not None:
        return algebraic
    names = set()
    for f in forms:
        match = re.match(r"([tyuzv])=\\log_", f) or re.search(r"=([tyuzv])$", f)
        if match:
            names.add(match[1])
    if len(names) != 1:
        return None
    name = next(iter(names))
    if any(
        re.search(r"(?<![A-Za-z])([tyuzv])=", f)
        and re.search(r"(?<![A-Za-z])([tyuzv])=", f)[1] != name
        for f in forms
    ):
        raise UnsupportedCondition(
            "only the original logarithm substitution may be retained"
        )
    if any(
        re.search(r"\((?:1\+" + name + "|" + name + r"\+1)\)\^\{?2\}?", f)
        for f in forms
    ):
        return "base_product", name
    if any(name + r"+\frac{1}{" + name + "}" in f for f in forms):
        return "reciprocal", name
    return None


def figure_stage(parent_html, kind):
    if kind == "base_square":
        from .exam_trigonometric_log_base_change_style import figure_stage as base_stage

        return base_stage(parent_html)
    soup = BeautifulSoup(parent_html, "html.parser")
    images = soup.find_all("img")
    if kind == "finite_base":
        if images:
            raise UnsupportedCondition(
                "the finite-base log parent has no source diagram"
            )
        return "none"
    if not images:
        return "none"
    if kind == "chain":
        if len(images) != 2 or any(im.find_parent("li") for im in images):
            raise UnsupportedCondition(
                "the chain identity needs its two separate outside source circles"
            )
        preceding = []
        for n in soup.descendants:
            if n is images[0]:
                break
            if getattr(n, "attrs", {}).get("data-inline-latex"):
                preceding.append(n)
        if preceding:
            raise UnsupportedCondition(
                "the domain circle must remain before the chain derivation"
            )
        before_selection = []
        for n in soup.descendants:
            if n is images[1]:
                break
            if getattr(n, "attrs", {}).get("data-inline-latex"):
                before_selection.append(clean(n["data-inline-latex"]))
        if (
            not before_selection
            or len(re.findall(r"(?<![A-Za-z])x&?=", before_selection[-1])) < 2
        ):
            raise UnsupportedCondition(
                "the selection circle must follow the complete chain-root families"
            )
        return "outside"
    if kind != "reciprocal" or len(images) != 1:
        raise UnsupportedCondition("the identity has an unreviewed figure inventory")
    part = images[0].find_parent("li")
    if part is None or part.get("data-list-marker") != "а)":
        raise UnsupportedCondition(
            "the reciprocal-log figure must remain in derivation part a"
        )
    forms = []
    for n in part.descendants:
        if n is images[0]:
            break
        if getattr(n, "attrs", {}).get("data-inline-latex"):
            forms.append(clean(n["data-inline-latex"]))
    if len(forms) != 2 or r"\log_" not in forms[0] or "^" not in forms[1]:
        raise UnsupportedCondition(
            "the source circle must follow the logarithm quadratic before back-substitution"
        )
    return "after-substitution"


def style(parent_html, formula):
    from .exam_trigonometric_log_variable import reviewed

    if not reviewed(formula):
        return None
    method = parent_kind(parent_html)
    if method is None:
        return None
    kind, _ = method
    stage = figure_stage(parent_html, kind)
    if kind == "finite_base":
        return S, False, False, "none", None, "inequalities"
    soup = BeautifulSoup(parent_html, "html.parser")
    text = " ".join(soup.get_text(" ").replace("\xad", "").lower().split())
    if stage == "none":
        selection = (
            "inequalities"
            if re.search(r"двойн\w*\s+неравенств", text)
            else "progressions"
            if "длина отрезка" in text
            else None
        )
        if selection is None:
            raise UnsupportedCondition(
                "the unillustrated identity must retain its original interval selection"
            )
    else:
        selection = "circle"
    return (
        C if kind in ("power", "base_square") else S,
        False,
        False,
        "after-intro" if stage == "after-substitution" else stage,
        None,
        selection,
    )
