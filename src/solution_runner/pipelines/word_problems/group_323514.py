"""Wallpaper-roll ceiling rule for source group 323514."""

from __future__ import annotations

from fractions import Fraction
import re
from typing import Any

from solution_runner.pipelines.core.numbers import parse_rational

from .common import UnsupportedCondition, decimal_latex, finalize, require_content


RULE = "word-problem-323514-wallpaper-rolls-ceiling"
_NUMBER = r"(?:0|[1-9]\d*)(?:[,.]\d+)?"
_CONDITION = re.compile(
    rf"Одного рулона обоев хватает для оклейки полосы от пола до потолка шириной (?P<width>{_NUMBER}) м\. "
    rf"(?:Какое наименьшее количество|Сколько) рулонов обоев нужно купить для оклейки прямоугольной комнаты размерами (?P<side_a>{_NUMBER}) м на (?P<side_b>{_NUMBER}) м\?"
)


def _fraction_latex(value: Fraction) -> str:
    return str(value.numerator) if value.denominator == 1 else rf"\frac{{{value.numerator}}}{{{value.denominator}}}"


def build_context_repair_plan(context: dict[str, Any]):
    _, condition, answer_section, solution_section, text = require_content(context)
    match = _CONDITION.fullmatch(text)
    if match is None:
        raise UnsupportedCondition("condition does not match group 323514 template")

    width, side_a, side_b = (parse_rational(match[name]) for name in ("width", "side_a", "side_b"))
    if width <= 0 or side_a <= 0 or side_b <= 0:
        raise UnsupportedCondition("room dimensions and roll width must be positive")
    perimeter = 2 * (side_a + side_b)
    quotient = perimeter / width
    rolls = -(-quotient.numerator // quotient.denominator)
    division = decimal_latex(quotient) if quotient.denominator in (1, 2, 4, 5, 8, 10, 20, 25, 40, 50, 100) else _fraction_latex(quotient)
    solution_html = (
        f'<p>Сначала найдём периметр комнаты: <span data-inline-latex="2\\cdot({decimal_latex(side_a)}+{decimal_latex(side_b)})={decimal_latex(perimeter)}"></span> м.</p>'
        f'<p>Число нужных полос равно <span data-inline-latex="\\frac{{{decimal_latex(perimeter)}}}{{{decimal_latex(width)}}}={division}"></span>. '
        f'Нужно купить целое число рулонов, поэтому потребуется {rolls} рулонов обоев.</p>'
    )
    return finalize(condition, answer_section, solution_section, rolls, solution_html)
