"""Plans for cancelling a difference of a squared binomial and its square terms."""

from __future__ import annotations

from fractions import Fraction
import re
from typing import Any

from bs4 import BeautifulSoup

from ..triangles.isosceles.planner import _normalized_content, _section, _section_transformation
from ..triangles.right.planner import RepairPlan, RightTrianglePlanError


_FORMULA = re.compile(
    r"^\((?P<x_square>\d*)x\^\{2\}(?P<outer_sign>[+-])(?P<y_square>\d*)y\^\{2\}"
    r"-\((?P<x_coefficient>\d*)x(?P<inner_sign>[+-])(?P<y_coefficient>\d*)y\)\^\{2\}\)"
    r"\\colon(?P<denominator>\(-?\d*xy\)|-?\d*xy)$"
)
_SQUARE_FIRST_FRACTION = re.compile(
    r"^\\frac\{\((?P<p>\d*)x(?P<sign>[+-])(?P<q>\d*)y\)\^\{2\}"
    r"-(?P<a>\d*)x\^\{2\}-(?P<b>\d*)y\^\{2\}\}\{(?P<den>-?\d*)xy\}$"
)
_SQUARE_FIRST_COLON = re.compile(
    r"^\(\((?P<p>\d*)x(?P<sign>[+-])(?P<q>\d*)y\)\^\{2\}"
    r"-(?P<a>\d*)x\^\{2\}-(?P<b>\d*)y\^\{2\}\)\\colon(?P<den>\(-?\d*xy\)|-?\d*xy)$"
)
_CONJUGATE_SQUARES_FRACTION = re.compile(
    r"^\\frac\{\((?P<p>\d*)x(?P<left_sign>[+-])(?P<q>\d*)y\)\^\{2\}"
    r"-\((?P<right_p>\d*)x(?P<right_sign>[+-])(?P<right_q>\d*)y\)\^\{2\}\}"
    r"\{(?P<den>-?\d*)xy\}$"
)
_CONJUGATE_SQUARES_COLON = re.compile(
    r"^\(\((?P<p>\d*)x(?P<left_sign>[+-])(?P<q>\d*)y\)\^\{2\}"
    r"-\((?P<right_p>\d*)x(?P<right_sign>[+-])(?P<right_q>\d*)y\)\^\{2\}\)"
    r"\\colon(?P<den>\(-?\d*xy\)|-?\d*xy)$"
)


def _number(value: str) -> int:
    return int(value or "1")


def _coefficient_term(value: int, variables: str) -> str:
    if abs(value) == 1:
        return variables if value > 0 else f"-{variables}"
    return f"{value}{variables}"


def _fraction_latex(value: Fraction) -> str:
    if value.denominator == 1:
        return str(value.numerator)
    prefix = "-" if value < 0 else ""
    return f"{prefix}\\frac{{{abs(value.numerator)}}}{{{value.denominator}}}"


def _formula(condition: dict[str, Any]) -> str:
    soup = BeautifulSoup(str(condition.get("html") or ""), "html.parser")
    formulas = soup.find_all("span", attrs={"data-inline-latex": True})
    if len(formulas) != 1:
        raise RightTrianglePlanError("condition must contain exactly one formula")
    return str(formulas[0].get("data-inline-latex") or "").replace(" ", "")


def _substitution_values(x_coefficient: int, y_coefficient: int, inner_sign: str) -> tuple[int, int]:
    """Start from x=y=1 and move only when the binomial would become zero."""

    if inner_sign == "-" and x_coefficient == y_coefficient:
        return 2, 1
    return 1, 1


def _square_first_plan(context: dict[str, Any], match: re.Match[str]) -> RepairPlan:
    """Plan the inverse order: a binomial square minus its square terms."""

    p, q, a, b = (_number(match[name]) for name in ("p", "q", "a", "b"))
    denominator = int(match["den"].strip("()").removesuffix("xy") or "1")
    if a != p**2 or b != q**2:
        raise RightTrianglePlanError("outer square terms do not match the binomial")
    cross = 2 * p * q if match["sign"] == "+" else -2 * p * q
    answer_value = Fraction(cross, denominator)
    answer = _fraction_latex(answer_value)
    binomial = f"{_coefficient_term(p, 'x')}{match['sign']}{_coefficient_term(q, 'y')}"
    flattened = (
        f"{_coefficient_term(a, 'x^{2}')}"
        f"{'+' if cross >= 0 else '-'}{_coefficient_term(abs(cross), 'xy')}"
        f"+{_coefficient_term(b, 'y^{2}')}-{_coefficient_term(a, 'x^{2}')}-{_coefficient_term(b, 'y^{2}')}"
    )
    denominator_term = _coefficient_term(denominator, "xy")
    numerator_term = _coefficient_term(cross, "xy")
    fraction = f"\\frac{{({binomial})^{{2}}-{_coefficient_term(a, 'x^{2}')}-{_coefficient_term(b, 'y^{2}')}}}{{{denominator_term}}}"
    primary = f"{fraction}=\\frac{{{flattened}}}{{{denominator_term}}}=\\frac{{{numerator_term}}}{{{denominator_term}}}={answer}"

    x_value, y_value = _substitution_values(p, q, match["sign"])
    inner_value = p * x_value + (q * y_value if match["sign"] == "+" else -q * y_value)
    numerator_value = inner_value**2 - a * x_value**2 - b * y_value**2
    denominator_value = denominator * x_value * y_value
    if not all((x_value, y_value, inner_value, numerator_value, denominator_value)):
        raise RightTrianglePlanError("no non-zero substitution was selected")
    alternative = (
        f"\\frac{{({p}\\cdot{x_value}{match['sign']}{q}\\cdot{y_value})^{{2}}-{a}\\cdot{x_value}^{{2}}-{b}\\cdot{y_value}^{{2}}}}"
        f"{{{denominator}\\cdot{x_value}\\cdot{y_value}}}="
        f"\\frac{{{inner_value}^{{2}}-{a * x_value**2}-{b * y_value**2}}}{{{denominator_value}}}="
        f"\\frac{{{numerator_value}}}{{{denominator_value}}}={answer}"
    )
    html = (
        f'<center><p><span data-inline-latex="{primary}"></span>.</p></center>'
        '<p><b>Приведём другое решение</b></p>'
        '<p>Так как это задание первой части, переменные <span data-inline-latex="x"></span> и '
        '<span data-inline-latex="y"></span> в ответе быть не могут, значит, они должны сократиться.</p>'
        f'<p>Подставим <span data-inline-latex="x={x_value},\\;y={y_value}"></span>:</p>'
        f'<center><p><span data-inline-latex="{alternative}"></span>.</p></center>'
    )
    content = _normalized_content(context)
    answer_section = _section(content, "answer")
    solution_section = _section(content, "solution")
    changes: list[dict[str, Any]] = []
    if solution_section is None or str(solution_section.get("html") or "") != html:
        changes.append(_section_transformation(solution_section, "solution", "Решение", html))
    current_answer = BeautifulSoup(str(answer_section.get("html") or "") if answer_section else "", "html.parser").get_text("", strip=True).replace(" ", "")
    if current_answer != answer:
        changes.append(_section_transformation(answer_section, "answer", "Ответ", f'<p><span data-effect="spaced">{answer}</span></p>'))
    return RepairPlan(answer=answer, transformations=tuple(changes))


def _conjugate_squares_plan(context: dict[str, Any], match: re.Match[str]) -> RepairPlan:
    """Plan a difference of squares whose binomials differ only by one sign."""

    p, q, right_p, right_q = (_number(match[name]) for name in ("p", "q", "right_p", "right_q"))
    if (p, q) != (right_p, right_q) or match["left_sign"] == match["right_sign"]:
        raise RightTrianglePlanError("binomials must be conjugates")
    denominator = int(match["den"].strip("()").removesuffix("xy") or "1")
    left_cross = 2 * p * q if match["left_sign"] == "+" else -2 * p * q
    right_cross = 2 * p * q if match["right_sign"] == "+" else -2 * p * q
    numerator_cross = left_cross - right_cross
    answer = _fraction_latex(Fraction(numerator_cross, denominator))
    left = f"{_coefficient_term(p, 'x')}{match['left_sign']}{_coefficient_term(q, 'y')}"
    right = f"{_coefficient_term(p, 'x')}{match['right_sign']}{_coefficient_term(q, 'y')}"
    x_square = _coefficient_term(p**2, "x^{2}")
    y_square = _coefficient_term(q**2, "y^{2}")
    left_expansion = f"{x_square}{'+' if left_cross >= 0 else '-'}{_coefficient_term(abs(left_cross), 'xy')}+{y_square}"
    right_expansion = f"{x_square}{'+' if right_cross >= 0 else '-'}{_coefficient_term(abs(right_cross), 'xy')}+{y_square}"
    denominator_term = _coefficient_term(denominator, "xy")
    numerator_term = _coefficient_term(numerator_cross, "xy")
    fraction = f"\\frac{{({left})^{{2}}-({right})^{{2}}}}{{{denominator_term}}}"
    difference_factors = (
        _coefficient_term(-2 * q if match["left_sign"] == "-" else 2 * q, "y"),
        _coefficient_term(2 * p, "x"),
    )
    first_solution = (
        f"{fraction}=\\frac{{(({left})-({right}))(({left})+({right}))}}{{{denominator_term}}}"
        f"=\\frac{{({left}-{right})({left}+{right})}}{{{denominator_term}}}"
        f"=\\frac{{{difference_factors[0]}\\cdot{difference_factors[1]}}}{{{denominator_term}}}"
        f"=\\frac{{{numerator_term}}}{{{denominator_term}}}={answer}"
    )
    second_solution = (
        f"{fraction}=\\frac{{(({_coefficient_term(p, 'x')})^{{2}}"
        f"{'+' if left_cross >= 0 else '-'}2\\cdot{_coefficient_term(p, 'x')}\\cdot{_coefficient_term(q, 'y')}+({_coefficient_term(q, 'y')})^{{2}})"
        f"-(({_coefficient_term(p, 'x')})^{{2}}{'+' if right_cross >= 0 else '-'}2\\cdot{_coefficient_term(p, 'x')}\\cdot{_coefficient_term(q, 'y')}+({_coefficient_term(q, 'y')})^{{2}})}}{{{denominator_term}}}"
        f"=\\frac{{({left_expansion})-({right_expansion})}}{{{denominator_term}}}"
        f"=\\frac{{{numerator_term}}}{{{denominator_term}}}={answer}"
    )

    x_value, y_value = _substitution_values(p, q, match["left_sign"])
    left_value = p * x_value + (q * y_value if match["left_sign"] == "+" else -q * y_value)
    right_value = p * x_value + (q * y_value if match["right_sign"] == "+" else -q * y_value)
    numerator_value = left_value**2 - right_value**2
    denominator_value = denominator * x_value * y_value
    if not all((x_value, y_value, left_value, right_value, numerator_value, denominator_value)):
        raise RightTrianglePlanError("no non-zero substitution was selected")
    alternative = (
        f"\\frac{{({p}\\cdot{x_value}{match['left_sign']}{q}\\cdot{y_value})^{{2}}-"
        f"({p}\\cdot{x_value}{match['right_sign']}{q}\\cdot{y_value})^{{2}}}}"
        f"{{{denominator}\\cdot{x_value}\\cdot{y_value}}}="
        f"\\frac{{({p * x_value}{match['left_sign']}{q * y_value})^{{2}}-({p * x_value}{match['right_sign']}{q * y_value})^{{2}}}}{{{denominator_value}}}="
        f"\\frac{{{left_value}^{{2}}-{right_value}^{{2}}}}{{{denominator_value}}}="
        f"\\frac{{{numerator_value}}}{{{denominator_value}}}={answer}"
    )
    html = (
        '<p>Используем формулу разности квадратов:</p>'
        '<center><p><span data-inline-latex="a^{2}-b^{2}=(a-b)(a+b)"></span>.</p></center>'
        f'<center><p><span data-inline-latex="{first_solution}"></span>.</p></center>'
        '<p><b>Приведём другое решение</b></p>'
        '<p>Используем формулу квадрата суммы и разности:</p>'
        '<center><p><span data-inline-latex="(a\\pm b)^{2}=a^{2}\\pm2ab+b^{2}"></span>.</p></center>'
        f'<center><p><span data-inline-latex="{second_solution}"></span>.</p></center>'
        '<p><b>Приведём другое решение</b></p>'
        '<p>Так как это задание первой части, переменные <span data-inline-latex="x"></span> и '
        '<span data-inline-latex="y"></span> в ответе быть не могут, значит, они должны сократиться.</p>'
        f'<p>Подставим <span data-inline-latex="x={x_value},\\;y={y_value}"></span>:</p>'
        f'<center><p><span data-inline-latex="{alternative}"></span>.</p></center>'
    )
    content = _normalized_content(context)
    answer_section = _section(content, "answer")
    solution_section = _section(content, "solution")
    changes: list[dict[str, Any]] = []
    if solution_section is None or str(solution_section.get("html") or "") != html:
        changes.append(_section_transformation(solution_section, "solution", "Решение", html))
    current_answer = BeautifulSoup(str(answer_section.get("html") or "") if answer_section else "", "html.parser").get_text("", strip=True).replace(" ", "")
    if current_answer != answer:
        changes.append(_section_transformation(answer_section, "answer", "Ответ", f'<p><span data-effect="spaced">{answer}</span></p>'))
    return RepairPlan(answer=answer, transformations=tuple(changes))


def build_context_repair_plan(context: dict[str, Any]) -> RepairPlan:
    """Expand the binomial square and cancel the common xy factor."""

    content = _normalized_content(context)
    condition = _section(content, "condition")
    if condition is None or content.get("assets") or tuple(condition.get("asset_keys") or ()):
        raise RightTrianglePlanError("square expansion condition must be text-only")
    expression = _formula(condition)
    if conjugate_match := (_CONJUGATE_SQUARES_FRACTION.fullmatch(expression) or _CONJUGATE_SQUARES_COLON.fullmatch(expression)):
        return _conjugate_squares_plan(context, conjugate_match)
    if square_first_match := (_SQUARE_FIRST_FRACTION.fullmatch(expression) or _SQUARE_FIRST_COLON.fullmatch(expression)):
        return _square_first_plan(context, square_first_match)
    match = _FORMULA.fullmatch(expression)
    if match is None:
        raise RightTrianglePlanError("condition does not match the registered square-expansion form")
    x_coefficient = _number(match["x_coefficient"])
    y_coefficient = _number(match["y_coefficient"])
    x_square = _number(match["x_square"])
    y_square = _number(match["y_square"])
    denominator_text = match["denominator"].strip("()")
    denominator = int(denominator_text.removesuffix("xy") or "1")
    if x_square != x_coefficient**2 or y_square != y_coefficient**2:
        raise RightTrianglePlanError("outer square terms do not match the squared binomial")
    if match["outer_sign"] != "+":
        raise RightTrianglePlanError("outer square terms must be added")
    cross_coefficient = 2 * x_coefficient * y_coefficient
    square_cross = cross_coefficient if match["inner_sign"] == "+" else -cross_coefficient
    numerator_cross = -square_cross
    answer_value = Fraction(numerator_cross, denominator)
    answer = _fraction_latex(answer_value)

    binomial = f"{_coefficient_term(x_coefficient, 'x')}{match['inner_sign']}{_coefficient_term(y_coefficient, 'y')}"
    square_expansion = (
        f"{_coefficient_term(x_square, 'x^{2}')}"
        f"{'+' if square_cross >= 0 else '-'}{_coefficient_term(abs(square_cross), 'xy')}"
        f"+{_coefficient_term(y_square, 'y^{2}')}"
    )
    flattened = (
        f"{_coefficient_term(x_square, 'x^{2}')}+{_coefficient_term(y_square, 'y^{2}')}"
        f"-{_coefficient_term(x_square, 'x^{2}')}"
        f"{'+' if numerator_cross >= 0 else '-'}{_coefficient_term(abs(numerator_cross), 'xy')}"
        f"-{_coefficient_term(y_square, 'y^{2}')}"
    )
    denominator_term = _coefficient_term(denominator, "xy")
    numerator_term = _coefficient_term(numerator_cross, "xy")
    fraction = f"\\frac{{{_coefficient_term(x_square, 'x^{2}')}+{_coefficient_term(y_square, 'y^{2}')}-({binomial})^{{2}}}}{{{denominator_term}}}"
    primary = (
        f"{fraction}=\\frac{{{_coefficient_term(x_square, 'x^{2}')}+{_coefficient_term(y_square, 'y^{2}')}-({square_expansion})}}{{{denominator_term}}}"
        f"=\\frac{{{flattened}}}{{{denominator_term}}}"
        f"=\\frac{{{numerator_term}}}{{{denominator_term}}}={answer}"
    )
    x_value, y_value = _substitution_values(x_coefficient, y_coefficient, match["inner_sign"])
    inner_value = x_coefficient * x_value + (
        y_coefficient * y_value if match["inner_sign"] == "+" else -y_coefficient * y_value
    )
    numerator_value = x_square * x_value**2 + y_square * y_value**2 - inner_value**2
    denominator_value = denominator * x_value * y_value
    if not all((x_value, y_value, inner_value, numerator_value, denominator_value)):
        raise RightTrianglePlanError("no non-zero substitution was selected")
    alternative = (
        f"\\frac{{{x_square}\\cdot{x_value}^{{2}}+{y_square}\\cdot{y_value}^{{2}}-"
        f"({x_coefficient}\\cdot{x_value}{match['inner_sign']}{y_coefficient}\\cdot{y_value})^{{2}}}}"
        f"{{{denominator}\\cdot{x_value}\\cdot{y_value}}}="
        f"\\frac{{{x_square * x_value**2}+{y_square * y_value**2}-{inner_value}^{{2}}}}{{{denominator_value}}}="
        f"\\frac{{{numerator_value}}}{{{denominator_value}}}={answer}"
    )
    html = (
        f'<center><p><span data-inline-latex="{primary}"></span>.</p></center>'
        '<p><b>Приведём другое решение</b></p>'
        '<p>Так как это задание первой части, переменные <span data-inline-latex="x"></span> и '
        '<span data-inline-latex="y"></span> в ответе быть не могут, значит, они должны сократиться. '
        '</p>'
        f'<p>Подставим <span data-inline-latex="x={x_value},\\;y={y_value}"></span>:</p>'
        f'<center><p><span data-inline-latex="{alternative}"></span>.</p></center>'
    )
    answer_section = _section(content, "answer")
    solution_section = _section(content, "solution")
    changes: list[dict[str, Any]] = []
    if solution_section is None or str(solution_section.get("html") or "") != html:
        changes.append(_section_transformation(solution_section, "solution", "Решение", html))
    current_answer = BeautifulSoup(str(answer_section.get("html") or "") if answer_section else "", "html.parser").get_text("", strip=True).replace(" ", "")
    if current_answer != answer:
        changes.append(_section_transformation(answer_section, "answer", "Ответ", f'<p><span data-effect="spaced">{answer}</span></p>'))
    return RepairPlan(answer=answer, transformations=tuple(changes))
