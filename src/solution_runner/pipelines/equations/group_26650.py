"""Fail-closed planner for elementary exponential equations."""

from __future__ import annotations

import re
from fractions import Fraction
from typing import Any

from bs4 import BeautifulSoup

from solution_runner.pipelines.core.numbers import (
    NumberFormatError,
    format_answer,
    format_latex_fraction,
)
from solution_runner.pipelines.equations.group_26656 import RepairPlan

from .exponential_affine import (
    _DIVIDED_SAME_BASE,
    _FORMULA,
    _MULTIPLIED_SAME_BASE,
    _NUMBER,
    _POWER_DIFFERENCE,
    _SCALED_POWER,
    _TWO_BASES,
    UnsupportedCondition,
    _answer_steps,
    _base_latex,
    _common_base_for_two_sides,
    _exponent,
    _fractional_common_base,
    _linear_latex,
    _parse_base,
    _parse_exponent,
    _parse_linear,
    _primitive_integer_base,
    _scaled_exponent,
    _variable_first_latex,
)
from .solution_formatting import vertical_derivation

RULE = "exponential-26650-common-base-affine-exponent"


__all__ = [
    "RULE",
    "_NUMBER",
    "UnsupportedCondition",
    "_answer_steps",
    "_exponent",
    "_linear_latex",
    "_parse_linear",
    "_rewrite",
    "_section",
    "build_context_repair_plan",
    "build_repair_plan",
]


def _section(content: dict[str, Any], key: str) -> dict[str, Any] | None:
    found = [s for s in content.get("sections", []) if s.get("key") == key]
    if len(found) > 1:
        raise UnsupportedCondition(f"multiple {key} sections")
    return found[0] if found else None


def _rewrite(
    section: dict[str, Any] | None, key: str, title: str, html: str
) -> dict[str, Any]:
    return {
        "transformation_target_id": str(
            (section or {}).get("transformation_target_id") or f"section:{key}"
        ),
        "operation": "rewrite" if section else "add",
        "value": {"title": title, "html": html, "asset_keys": []},
    }


def _solution_signature(html: str) -> tuple[tuple[str, ...], str] | None:
    soup = BeautifulSoup(html, "html.parser")
    formulas = [
        str(span.get("data-inline-latex") or "")
        for span in soup.find_all("span")
        if span.has_attr("data-inline-latex")
    ]
    if not formulas or any(not formula for formula in formulas):
        return None
    prose = re.sub(
        r"\s+",
        " ",
        soup.get_text(" ", strip=True).replace("\u00ad", "").replace("ё", "е"),
    ).strip()
    return tuple(formulas), prose


def _expanded_plan(
    formula: str, normalized: str, intermediate: tuple[str, ...] = ()
) -> RepairPlan:
    plan = build_repair_plan(normalized)
    marker = f"{normalized}\\iff "
    if marker not in plan.solution_html:
        raise UnsupportedCondition("normalized exponential derivation is missing")
    expansion = r"\iff ".join((formula, *intermediate, normalized)) + r"\iff "
    html = plan.solution_html.replace(marker, expansion, 1)
    return RepairPlan(answer=plan.answer, condition_html="", solution_html=html)


def _scaled_power_plan(formula: str, scaled: re.Match[str]) -> RepairPlan:
    factor = _parse_base(scaled["factor"])
    base = _parse_base(scaled["base"])
    if factor <= 0 or base <= 0 or base == 1:
        raise UnsupportedCondition(
            "scaled powers require a positive factor and valid base"
        )
    if re.fullmatch(_NUMBER, scaled["right"]):
        right = _parse_base(scaled["right"]) / factor
        normalized = (
            f"{scaled['base']}^{{{scaled['exponent']}}}={format_latex_fraction(right)}"
        )
    else:
        factor_power = _exponent(factor, base)
        constant, coefficient = _parse_exponent(scaled["exponent"])
        if not isinstance(constant, int) or not isinstance(coefficient, int):
            raise UnsupportedCondition(
                "scaled two-sided powers require integer affine exponents"
            )
        exponent = _variable_first_latex(constant + factor_power, coefficient)
        normalized = f"{scaled['base']}^{{{exponent}}}={scaled['right']}"
    return _expanded_plan(formula, normalized)


def _power_difference_plan(formula: str, difference: re.Match[str]) -> RepairPlan:
    base = _parse_base(difference["base"])
    left_constant, left_coefficient = _parse_exponent(difference["left_exponent"])
    right_constant, right_coefficient = _parse_exponent(difference["right_exponent"])
    shift = left_constant - right_constant
    if (
        left_coefficient != right_coefficient
        or not isinstance(shift, int)
        or not right_coefficient
    ):
        raise UnsupportedCondition("power difference requires a constant integer shift")
    factor = base**shift - 1
    if not factor:
        raise UnsupportedCondition("power difference has no unique root")
    right = _parse_base(difference["right"]) / factor
    if right <= 0:
        raise UnsupportedCondition("power difference has no real root")
    normalized = f"{difference['base']}^{{{difference['right_exponent']}}}={format_latex_fraction(right)}"
    power = f"{difference['base']}^{{{difference['right_exponent']}}}"
    factored = (
        f"{power}\\cdot ({difference['base']}^{{{shift}}}-1)={difference['right']}"
    )
    simplified = f"{format_latex_fraction(factor)}\\cdot {power}={difference['right']}"
    return _expanded_plan(formula, normalized, (factored, simplified))


def _combined_power_plan(formula: str, combined_match: re.Match[str]) -> RepairPlan:
    left_constant, left_coefficient = _parse_exponent(
        combined_match.group("left_exponent")
    )
    right_constant, right_coefficient = _parse_exponent(
        combined_match.group("right_exponent")
    )
    is_division = "\\colon" in formula
    exponent = _variable_first_latex(
        left_constant - right_constant
        if is_division
        else left_constant + right_constant,
        left_coefficient - right_coefficient
        if is_division
        else left_coefficient + right_coefficient,
    )
    combined = (
        f"{combined_match.group('base')}^{{{exponent}}}={combined_match.group('right')}"
    )
    collapsed = build_repair_plan(combined)
    marker = f"{combined}\\iff "
    if marker not in collapsed.solution_html:
        raise UnsupportedCondition("collapsed division solution is malformed")
    solution_html = collapsed.solution_html.replace(
        marker,
        f"{formula}\\iff {combined}\\iff ",
        1,
    )
    return RepairPlan(
        answer=collapsed.answer,
        condition_html="",
        solution_html=solution_html,
    )


def _two_bases_plan(formula: str, two: re.Match[str]) -> RepairPlan:
    try:
        left_base = _parse_base(two.group("left_base"))
        right_base = _parse_base(two.group("right_base"))
    except ValueError as e:
        raise UnsupportedCondition("bases are unsupported") from e
    common, left_factor = _common_base_for_two_sides(left_base)
    common_right, right_factor = _common_base_for_two_sides(right_base)
    if common != common_right:
        raise UnsupportedCondition("bases do not reduce to one common base")
    left_constant, left_coefficient = _parse_exponent(two.group("left_exponent"))
    right_constant, right_coefficient = _parse_exponent(two.group("right_exponent"))
    coefficient = left_factor * left_coefficient - right_factor * right_coefficient
    constant = left_factor * left_constant - right_factor * right_constant
    if coefficient == 0:
        raise UnsupportedCondition("equation has no unique root")
    result = Fraction(-constant, coefficient)
    try:
        answer = format_answer(result)
    except NumberFormatError as e:
        raise UnsupportedCondition("answer does not terminate") from e
    left = _scaled_exponent(two.group("left_exponent"), left_factor)
    right = _scaled_exponent(two.group("right_exponent"), right_factor)
    base_latex = _base_latex(common)
    moved_coefficient = (
        right_factor * right_coefficient - left_factor * left_coefficient
    )
    moved_constant = left_factor * left_constant - right_factor * right_constant
    moved_x = _variable_first_latex(0, moved_coefficient)
    common_base_step = (
        ""
        if left_base == right_base and left_factor == right_factor == 1
        else f"{base_latex}^{{{left}}}={base_latex}^{{{right}}}\\iff "
    )
    solution = (
        "<p>Перейдём к одному основанию степени:</p>"
        f'<center><p><span data-inline-latex="{formula}\\iff {common_base_step}{left}={right}\\iff {format_latex_fraction(Fraction(moved_constant))}={moved_x}\\iff {_answer_steps(result)}"></span>.</p></center>'
    )
    return RepairPlan(answer=answer, condition_html="", solution_html=solution)


def build_repair_plan(formula: str) -> RepairPlan:
    scaled = _SCALED_POWER.fullmatch(formula)
    if scaled:
        return _scaled_power_plan(formula, scaled)
    difference = _POWER_DIFFERENCE.fullmatch(formula)
    if difference:
        return _power_difference_plan(formula, difference)
    combined_match = _DIVIDED_SAME_BASE.fullmatch(
        formula
    ) or _MULTIPLIED_SAME_BASE.fullmatch(formula)
    if combined_match:
        return _combined_power_plan(formula, combined_match)
    two = _TWO_BASES.fullmatch(formula)
    if two:
        return _two_bases_plan(formula, two)
    m = _FORMULA.fullmatch(formula)
    if not m:
        raise UnsupportedCondition("unsupported exponential equation")
    base_token = m.group("base")
    try:
        base = _parse_base(base_token)
        right = _parse_base(m.group("right"))
    except ValueError as e:
        raise UnsupportedCondition("base or right side is unsupported") from e
    if "{,}" in base_token:
        common_base, base_factor, power = base, 1, _exponent(right, base)
    elif base.numerator == 1 and base.denominator > 1 and right.denominator > 1:
        common_base, base_factor = _fractional_common_base(base)
        power = _exponent(right, common_base)
    elif base.numerator == 1 and base.denominator > 1:
        reciprocal = Fraction(base.denominator)
        try:
            common_base, base_factor, power = (
                reciprocal,
                -1,
                _exponent(right, reciprocal),
            )
        except UnsupportedCondition:
            common_base, base_factor = _primitive_integer_base(base)
            power = _exponent(right, common_base)
    else:
        try:
            # Prefer the condition's own base whenever the right side is already
            # an exact power of it; this preserves the parent's presentation.
            common_base, base_factor, power = base, 1, _exponent(right, base)
        except UnsupportedCondition:
            common_base, base_factor = _primitive_integer_base(base)
            power = _exponent(right, common_base)
    constant, coefficient = _parse_exponent(m.group("exponent"))
    if not coefficient:
        raise UnsupportedCondition("exponent must depend on x")
    result = Fraction(power - base_factor * constant, base_factor * coefficient)
    try:
        answer = format_answer(result)
    except NumberFormatError as e:
        raise UnsupportedCondition("answer does not terminate") from e
    exponent = _scaled_exponent(m.group("exponent"), base_factor)
    base_latex = _base_latex(common_base)
    right_power = f"{base_latex}^{{{power}}}"
    solution = (
        "<p>Перейдём к одному основанию степени:</p>"
        f'<center><p><span data-inline-latex="{formula}\\iff {base_latex}^{{{exponent}}}={right_power}\\iff {exponent}={power}\\iff {_answer_steps(result)}"></span>.</p></center>'
    )
    return RepairPlan(answer=answer, condition_html="", solution_html=solution)


def _condition_formula(condition_html: str) -> tuple[str, bool, tuple[str, str]]:
    raw = condition_html
    soup = BeautifulSoup(raw, "html.parser")
    spans = soup.find_all("span")
    normalize_condition = False
    if (
        len(spans) == 1
        and not spans[0].get_text("", strip=True)
        and set(spans[0].attrs) == {"data-inline-latex"}
    ):
        formula_span = spans[0]
        normalize_condition = formula_span.parent.name != "p"
        formula = str(formula_span.get("data-inline-latex") or "")
        formula_span.replace_with(formula)
    else:
        match = re.search(
            r"(?P<a>\d+)<sup>(?P<ae>.*?)</sup>\s*=\s*(?P<b>\d+)(?:<sup>(?P<be>.*?)</sup>)?",
            raw,
        )
        if not match:
            raise UnsupportedCondition("condition equation is ambiguous")
        clean = lambda value: re.sub(
            r"\s+", "", BeautifulSoup(value, "html.parser").get_text()
        ).replace("−", "-")
        right_exponent = match.group("be")
        right = (
            match.group("b")
            if right_exponent is None
            else f"{match.group('b')}^{{{clean(right_exponent)}}}"
        )
        formula = f"{match.group('a')}^{{{clean(match.group('ae'))}}}={right}"
        soup = BeautifulSoup(
            f"<p>Найдите корень уравнения {formula}.</p>", "html.parser"
        )
    visible = re.sub(
        r"\s+([.])",
        r"\1",
        " ".join(soup.get_text(" ", strip=True).replace("\u00ad", "").split()),
    )
    matched = next(
        (
            (intro, end)
            for intro in (
                "Найдите корень уравнения",
                "Найдите корень уравнения:",
                "Найдите решение уравнения",
                "Найдите решение уравнения:",
                "Решите уравнение",
                "Решите уравнение:",
            )
            for end in ("", ".")
            if visible == f"{intro} {formula}{end}"
        ),
        None,
    )
    if matched is None:
        raise UnsupportedCondition("condition wording is unsupported")
    return formula, normalize_condition, matched


def build_context_repair_plan(context: dict[str, Any]) -> RepairPlan:
    content = context.get("normalized_content")
    if (
        not isinstance(content, dict)
        or content.get("format") != "teacherhelper-normalized"
        or content.get("schema_version") != 3
        or content.get("assets") not in (None, [])
    ):
        raise UnsupportedCondition("normalized assetless content is required")
    condition, answer, solution = (
        _section(content, k) for k in ("condition", "answer", "solution")
    )
    if condition is None or tuple(condition.get("asset_keys") or ()):
        raise UnsupportedCondition("canonical condition is required")
    formula, normalize_condition, matched = _condition_formula(
        str(condition.get("html") or "")
    )
    planned = build_repair_plan(formula)
    changes = []
    solution_html = vertical_derivation(planned.solution_html)
    if normalize_condition:
        intro, end = matched
        changes.append(
            _rewrite(
                condition,
                "condition",
                "Условие",
                f'<p>{intro} <span data-inline-latex="{formula}"></span>{end}</p>',
            )
        )
    if solution is None or _solution_signature(
        str(solution.get("html") or "")
    ) != _solution_signature(solution_html):
        changes.append(_rewrite(solution, "solution", "Решение", solution_html))
    current = (
        BeautifulSoup(str(answer.get("html") or "") if answer else "", "html.parser")
        .get_text("", strip=True)
        .replace(" ", "")
    )
    if current != planned.answer:
        changes.append(
            _rewrite(
                answer,
                "answer",
                "Ответ",
                f'<p><span data-effect="spaced">{planned.answer}</span></p>',
            )
        )
    return RepairPlan(
        answer=planned.answer,
        condition_html=str(condition.get("html") or ""),
        solution_html=solution_html,
        transformations=tuple(changes),
    )
