"""Two-method solver for equal-exponent equations with a scalar multiplier."""
from __future__ import annotations

import re
from fractions import Fraction
from typing import Any

from bs4 import BeautifulSoup

from solution_runner.pipelines.core.numbers import NumberFormatError, format_answer, format_latex_fraction, parse_rational
from solution_runner.pipelines.equations.group_26650 import (
    _NUMBER, _answer_steps, _exponent, _linear_latex, _parse_linear,
    _section, _rewrite,
)
from solution_runner.pipelines.equations.group_26656 import RepairPlan

RULE = "exponential-77379-equal-exponent-different-bases"
_FORMULA = re.compile(
    rf"(?P<left>{_NUMBER})\^\{{(?P<exponent>[^{{}}]+)\}}="
    rf"(?P<factor>(?:{_NUMBER}|0\{{,\}}0*[1-9]\d*))\\cdot(?P<right>{_NUMBER})\^\{{(?P=exponent)\}}"
)


class UnsupportedCondition(ValueError):
    pass


def _base_latex(value: Fraction) -> str:
    latex = format_latex_fraction(value)
    return latex if value.denominator == 1 else f"(\\frac{{{value.numerator}}}{{{value.denominator}}})"


def _subtract_exponent_shift(source: str, shift: int) -> str:
    """Render ``source - shift`` without changing the linear coefficient."""
    constant, coefficient = _parse_linear(source)
    return _linear_latex(constant - shift, coefficient)


def _solution_signature(html: str) -> str:
    """Compare every prose and LaTeX node; this runner has two LaTeX formulas."""
    soup = BeautifulSoup(html, "html.parser")
    for span in soup.find_all("span", attrs={"data-inline-latex": True}):
        span["data-inline-latex"] = re.sub(r"\s+", "", str(span["data-inline-latex"])).replace("е", "ё")
    return re.sub(r"\s+", " ", str(soup).replace("\u00ad", "")).strip()


def _build_plan(formula: str) -> RepairPlan:
    match = _FORMULA.fullmatch(formula)
    if not match:
        raise UnsupportedCondition("unsupported equal-exponent equation")
    try:
        left = parse_rational(match.group("left").strip("()"))
        factor = parse_rational(match.group("factor").strip("()"))
        right = parse_rational(match.group("right").strip("()"))
    except ValueError as error:
        raise UnsupportedCondition("base or multiplier is unsupported") from error
    if left <= 0 or right <= 0 or left == right:
        raise UnsupportedCondition("bases must be distinct positive values")
    ratio = left / right
    try:
        shift = _exponent(factor, ratio)
    except ValueError as error:
        raise UnsupportedCondition("multiplier is not an exact power of the base ratio") from error
    constant, coefficient = _parse_linear(match.group("exponent"))
    result = Fraction(shift - constant, coefficient)
    try:
        answer = format_answer(result)
    except NumberFormatError as error:
        raise UnsupportedCondition("answer does not terminate") from error
    exponent = match.group("exponent")
    ratio_latex = _base_latex(ratio)
    primary = (
        f"{formula}\\iff \\frac{{{match.group('left')}^{{{exponent}}}}}{{{match.group('right')}^{{{exponent}}}}}={match.group('factor')}"
        f"\\iff {ratio_latex}^{{{exponent}}}={ratio_latex}^{{{shift}}}"
        f"\\iff {exponent}={shift}\\iff {_answer_steps(result)}"
    )
    shifted = _subtract_exponent_shift(exponent, shift)
    factor_latex = format_latex_fraction(factor)
    alternative = (
        f"{match.group('left')}^{{{exponent}}}={match.group('factor')}\\cdot{match.group('right')}^{{{exponent}}}"
        f"\\iff {match.group('left')}^{{{exponent}}}={factor_latex}\\cdot {match.group('right')}^{{{exponent}}}"
        f"\\iff \\frac{{{match.group('left')}^{{{exponent}}}}}{{{match.group('left')}^{{{shift}}}}}="
        f"\\frac{{{match.group('right')}^{{{exponent}}}}}{{{match.group('right')}^{{{shift}}}}}"
        f"\\iff {match.group('left')}^{{{shifted}}}={match.group('right')}^{{{shifted}}}"
    )
    html = (
        f'<center><p><span data-inline-latex="{primary}"></span>.</p></center>'
        "<p><strong>Альтернативное решение</strong></p>"
        f'<center><p><span data-inline-latex="{alternative}"></span>.</p></center>'
        "<p>Разные числа в одинаковой степени могут быть равны, только когда оба значения равны единице. Значит, показатель степени равен нулю:</p>"
        f'<center><p><span data-inline-latex="{shifted}=0\\iff {_answer_steps(result)}"></span>.</p></center>'
    )
    return RepairPlan(answer=answer, condition_html="", solution_html=html)


def build_context_repair_plan(context: dict[str, Any]) -> RepairPlan:
    content = context.get("normalized_content")
    if not isinstance(content, dict) or content.get("format") != "teacherhelper-normalized" or content.get("schema_version") != 3 or content.get("assets") not in (None, []):
        raise UnsupportedCondition("normalized assetless content is required")
    condition, answer, solution = (_section(content, key) for key in ("condition", "answer", "solution"))
    if condition is None or tuple(condition.get("asset_keys") or ()):
        raise UnsupportedCondition("canonical condition is required")
    soup = BeautifulSoup(str(condition.get("html") or ""), "html.parser")
    spans = soup.find_all("span")
    if len(spans) != 1 or spans[0].get_text("", strip=True) or set(spans[0].attrs) != {"data-inline-latex"}:
        raise UnsupportedCondition("condition equation is ambiguous")
    formula = str(spans[0].get("data-inline-latex") or "")
    spans[0].replace_with(formula)
    visible = re.sub(r"\s+([.])", r"\1", " ".join(soup.get_text(" ", strip=True).replace("\u00ad", "").split()))
    if not any(visible == f"{intro} {formula}{end}" for intro in ("Решите уравнение", "Решите уравнение:", "Найдите корень уравнения", "Найдите корень уравнения:") for end in ("", ".")):
        raise UnsupportedCondition("condition wording is unsupported")
    planned = _build_plan(re.sub(r"\s+", "", formula))
    changes = []
    if solution is None or _solution_signature(str(solution.get("html") or "")) != _solution_signature(planned.solution_html):
        changes.append(_rewrite(solution, "solution", "Решение", planned.solution_html))
    current = BeautifulSoup(str(answer.get("html") or "") if answer else "", "html.parser").get_text("", strip=True).replace(" ", "")
    if current != planned.answer:
        changes.append(_rewrite(answer, "answer", "Ответ", f'<p><span data-effect="spaced">{planned.answer}</span></p>'))
    return RepairPlan(answer=planned.answer, condition_html=str(condition.get("html") or ""), solution_html=planned.solution_html, transformations=tuple(changes))
