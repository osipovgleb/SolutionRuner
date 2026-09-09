"""Medicine-course rounding-up rule for source group 26624."""

from __future__ import annotations

from fractions import Fraction
import re
from typing import Any

from solution_runner.pipelines.core.numbers import format_answer, parse_rational, terminating_decimal_places

from .common import UnsupportedCondition, decimal_latex, finalize, require_content


RULE = "word-problem-26624-medicine-course-ceiling"
_NUMBER = r"(?:0|[1-9]\d*)(?:[,.]\d+)?"
_CONDITION = re.compile(
    rf"Больному прописано лекарство, которое нужно (?:пить|принимать) по (?P<dose>{_NUMBER}) г "
    r"(?P<times>[1-9]\d*) раза? в день в течение (?P<days>[1-9]\d*) (?:день|дня|дней)\. "
    rf"В одной упаковке (?P<tablets>[1-9]\d*) таблеток(?: лекарства)? по (?P<tablet_dose>{_NUMBER}) ?г\.? "
    r"Какого наименьшего количества упаковок хватит на весь курс лечения\?"
)


def _package_word(value: int) -> str:
    if value % 10 == 1 and value % 100 != 11:
        return "упаковку"
    if value % 10 in (2, 3, 4) and value % 100 not in (12, 13, 14):
        return "упаковки"
    return "упаковок"


def _plain_decimal(value: Fraction) -> str:
    """Render a number for prose; LaTeX braces belong only inside formulas."""

    return format_answer(value)


def _scaled_fraction_latex(value: Fraction, scale: int) -> tuple[int, int]:
    scaled = value * scale
    if scaled.denominator != 1:
        raise UnsupportedCondition("decimal scale is not exact")
    return scaled.numerator, scale


def _repeating_decimal_latex(value: Fraction) -> str:
    whole, remainder = divmod(value.numerator, value.denominator)
    digits: list[str] = []
    seen: dict[int, int] = {}
    while remainder and remainder not in seen:
        seen[remainder] = len(digits)
        remainder *= 10
        digit, remainder = divmod(remainder, value.denominator)
        digits.append(str(digit))
    if not remainder:
        return f"{whole}{{,}}{''.join(digits)}"
    start = seen[remainder]
    return f"{whole}{{,}}{''.join(digits[:start])}({''.join(digits[start:])})"


def _division_latex(required: Fraction, capacity: Fraction) -> str:
    quotient = required / capacity
    if quotient.denominator == 1:
        return rf"\frac{{{decimal_latex(required)}}}{{{decimal_latex(capacity)}}}={quotient.numerator}"
    if terminating_decimal_places(quotient) is None:
        return rf"\frac{{{decimal_latex(required)}}}{{{decimal_latex(capacity)}}}={_repeating_decimal_latex(quotient)}"

    places = max(terminating_decimal_places(required) or 0, terminating_decimal_places(capacity) or 0)
    numerator, _ = _scaled_fraction_latex(required, 10**places)
    denominator, _ = _scaled_fraction_latex(capacity, 10**places)
    prefix = rf"\frac{{{decimal_latex(required)}}}{{{decimal_latex(capacity)}}}="
    if (numerator, denominator) != (required.numerator, capacity.numerator):
        prefix += rf"\frac{{{numerator}}}{{{denominator}}}="
    raw_places = terminating_decimal_places(Fraction(1, denominator))
    reduced = Fraction(numerator, denominator)
    if raw_places is None and (reduced.numerator, reduced.denominator) != (numerator, denominator):
        prefix += rf"\frac{{{reduced.numerator}}}{{{reduced.denominator}}}="
    if raw_places is not None:
        chosen_numerator, chosen_denominator, decimal_places = numerator, denominator, raw_places
    else:
        chosen_numerator, chosen_denominator = reduced.numerator, reduced.denominator
        decimal_places = terminating_decimal_places(reduced) or 0
    target = 10**decimal_places
    multiplier = target // chosen_denominator
    return prefix + (
        rf"\frac{{{chosen_numerator}\cdot {multiplier}}}{{{chosen_denominator}\cdot {multiplier}}}="
        rf"\frac{{{chosen_numerator * multiplier}}}{{{target}}}={decimal_latex(quotient)}"
    )


def _legacy_division_latex(required: Fraction, capacity: Fraction) -> str:
    """Reproduce the first released template only to repair its exact output."""

    quotient = required / capacity
    whole = quotient.numerator // quotient.denominator
    remainder = quotient - whole
    if remainder == 0 or terminating_decimal_places(quotient) is None:
        return _division_latex(required, capacity)
    places = max(terminating_decimal_places(required) or 0, terminating_decimal_places(capacity) or 0)
    numerator, _ = _scaled_fraction_latex(required, 10**places)
    denominator, _ = _scaled_fraction_latex(capacity, 10**places)
    whole_part = whole * denominator
    rest = numerator - whole_part
    rest_fraction = Fraction(rest, denominator)
    return (
        rf"\frac{{{decimal_latex(required)}}}{{{decimal_latex(capacity)}}}="
        rf"\frac{{{numerator}}}{{{denominator}}}="
        rf"\frac{{{whole_part}+{rest}}}{{{denominator}}}="
        rf"\frac{{{whole_part}}}{{{denominator}}}+\frac{{{rest_fraction.numerator}}}{{{rest_fraction.denominator}}}="
        f"{decimal_latex(quotient)}"
    )


def build_context_repair_plan(context: dict[str, Any]):
    _, condition, answer_section, solution_section, text = require_content(context)
    match = _CONDITION.fullmatch(text)
    if match is None:
        raise UnsupportedCondition("condition does not match group 26624 template")

    dose = parse_rational(match["dose"])
    tablet_dose = parse_rational(match["tablet_dose"])
    times, days, tablets = (int(match[name]) for name in ("times", "days", "tablets"))
    required = dose * times * days
    capacity = tablet_dose * tablets
    if capacity <= 0:
        raise UnsupportedCondition("package capacity must be positive")
    quotient = required / capacity
    packages = -(-quotient.numerator // quotient.denominator)
    solution_html = (
        f'<p>Больному нужно принять <span data-inline-latex="{decimal_latex(dose)}\\cdot {times}\\cdot {days}={decimal_latex(required)}"></span> г лекарства. '
        f'В одной упаковке содержится <span data-inline-latex="{decimal_latex(tablet_dose)}\\cdot {tablets}={decimal_latex(capacity)}"></span> г лекарства. Разделим {_plain_decimal(required)} на {_plain_decimal(capacity)}:</p>'
        f'<center><p><span data-inline-latex="{_division_latex(required, capacity)}"></span>.</p></center>'
        f"<p>Значит, на курс лечения необходимо {packages} {_package_word(packages)}.</p>"
    )
    legacy_solution_html = (
        f'<p>Больному нужно принять <span data-inline-latex="{decimal_latex(dose)}\\cdot {times}\\cdot {days}={decimal_latex(required)}"></span> г лекарства. '
        f'В одной упаковке содержится <span data-inline-latex="{decimal_latex(tablet_dose)}\\cdot {tablets}={decimal_latex(capacity)}"></span> г лекарства. Разделим {decimal_latex(required)} на {decimal_latex(capacity)}:</p>'
        f'<center><p><span data-inline-latex="{_legacy_division_latex(required, capacity)}"></span>.</p></center>'
        f"<p>Значит, на курс лечения необходимо {packages} {_package_word(packages)}.</p>"
    )
    return finalize(
        condition,
        answer_section,
        solution_section,
        packages,
        solution_html,
        legacy_solution_html=legacy_solution_html,
    )
