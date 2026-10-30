"""Prepare a visible syntax repair only when the source solution confirms it."""

import re
from copy import deepcopy
from dataclasses import replace

from bs4 import BeautifulSoup

from ..probability.common import UnsupportedCondition
from ..triangles.isosceles.planner import (
    _normalized_content,
    _section,
    _section_transformation,
)
from .expression_condition import read_math_markup
from .verified_expression_repair import repair_verified_condition


def _compact(text):
    text = "".join(
        text.replace(r"\left", "").replace(r"\right", "").replace("−", "-").split()
    )
    return re.sub(r"\^\{(\d)\}", r"^\1", text)


def repair_terminal_product(context):
    content = _normalized_content(context)
    condition = _section(content, "condition")
    if condition is None:
        return context, None
    soup = BeautifulSoup(condition.get("html", ""), "html.parser")
    formulas = soup.select("[data-inline-latex]")
    if not formulas or not formulas[-1]["data-inline-latex"].rstrip().endswith(
        r"\cdot"
    ):
        return context, None
    _, _, values, text = read_math_markup(context, indexed=True)
    original = formulas[0]["data-inline-latex"]
    fragmented = len(formulas) > 1
    if fragmented:
        prefix = "Найдите значение выражения "
        if not text.startswith(prefix):
            return context, None
        original = text[len(prefix) :].removesuffix(".")
        for index in reversed(range(len(values))):
            original = original.replace("\ufff0" + str(index), values[index])
        if not re.fullmatch(r"[\s\d{}()\\a-z+−–*/^.-]+", original):
            return context, None
    candidate = original.rstrip()[:-5].rstrip()
    solution = _section(content, "solution")
    source = BeautifulSoup((solution or {}).get("html", ""), "html.parser").select(
        "[data-inline-latex]"
    )
    if (
        not source
        or "=" not in source[0]["data-inline-latex"]
        or _compact(source[0]["data-inline-latex"].split("=", 1)[0])
        != _compact(candidate)
    ):
        raise UnsupportedCondition(
            "the complete expression is not confirmed by the source solution"
        )
    if fragmented:
        soup = BeautifulSoup(
            "<p>Найдите значение выражения <span></span></p>", "html.parser"
        )
        soup.span["data-inline-latex"] = candidate
    else:
        formulas[0]["data-inline-latex"] = candidate
    copied = deepcopy(context)
    fixed = _section(copied["normalized_content"], "condition")
    fixed["html"] = str(soup)
    change = _section_transformation(condition, "condition", "Условие", fixed["html"])
    return copied, change


def repair_expression_condition(context):
    prepared, change = repair_verified_condition(context)
    return (prepared, change) if change else repair_terminal_product(context)


def with_condition_repair(plan, change):
    return (
        replace(plan, transformations=(change, *plan.transformations))
        if change
        else plan
    )
