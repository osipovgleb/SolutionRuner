"""Strict planner for source group 509214: integer linear equations."""

from __future__ import annotations

from fractions import Fraction
import re
from typing import Any

from bs4 import BeautifulSoup

from solution_runner.pipelines.core.numbers import (
    NumberFormatError,
    format_answer,
    parse_rational,
    terminating_decimal_places,
)
from solution_runner.pipelines.equations.group_26656 import RepairPlan


RULE = "elementary-equations-509214-linear-equation"

_CONDITION_INTRO = "Най\u00adди\u00adте ко\u00adрень урав\u00adне\u00adния"
_SOLUTION_INTRO = "По\u00adсле\u00adдо\u00adва\u00adтельно по\u00adлу\u00adча\u00adем:"
_TERM = re.compile(r"[+-]?(?:\d+x|\d+|x)")
_PARENTHESIZED_TERM = re.compile(r"(?P<multiplier>[+-]?\d+)\((?P<inner>[^()]+)\)")


class UnsupportedCondition(ValueError):
    """Raised before any transformation for a condition outside this grammar."""


def _section(content: dict[str, Any], key: str) -> dict[str, Any] | None:
    matches = [
        section
        for section in content.get("sections", [])
        if isinstance(section, dict) and section.get("key") == key
    ]
    if len(matches) > 1:
        raise UnsupportedCondition(f"multiple {key} sections")
    return matches[0] if matches else None


def _target(section: dict[str, Any] | None, key: str) -> str:
    if section is not None:
        target = str(section.get("transformation_target_id") or "")
        if target:
            return target
        section_id = str(section.get("section_id") or "")
        if section_id:
            return f"section:{section_id}"
    return f"section:{key}"


def _rewrite(
    section: dict[str, Any] | None,
    key: str,
    title: str,
    html: str,
) -> dict[str, Any]:
    return {
        "transformation_target_id": _target(section, key),
        "operation": "rewrite" if section is not None else "add",
        "value": {"title": title, "html": html, "asset_keys": []},
    }


def _term_values(token: str) -> tuple[int, int]:
    """Return the constant and x coefficient represented by one simple term."""

    if token.endswith("x"):
        coefficient_token = token[:-1]
        coefficient = (
            -1
            if coefficient_token == "-"
            else 1
            if coefficient_token in ("", "+")
            else int(coefficient_token)
        )
        return 0, coefficient
    return int(token), 0


def _simple_terms(side: str) -> list[tuple[int, int]]:
    matches = list(_TERM.finditer(side))
    if not matches or "".join(match.group(0) for match in matches) != side:
        raise UnsupportedCondition("side contains unsupported terms")
    return [_term_values(match.group(0)) for match in matches]


def _parse_side(side: str) -> tuple[int, int]:
    """Return ``constant, coefficient`` for exactly one constant plus one x-term."""

    terms = _simple_terms(side)
    if len(terms) != 2:
        raise UnsupportedCondition("each side must contain one integer and one x-term")

    constant = sum(term[0] for term in terms)
    coefficient = sum(term[1] for term in terms)
    if not any(term[1] == 0 for term in terms) or coefficient == 0:
        raise UnsupportedCondition("each side must contain one nonzero x-term")
    return constant, coefficient


def _parse_affine_side(side: str) -> tuple[int, int]:
    """Return the value of a simple affine side used beside parentheses."""

    terms = _simple_terms(side)
    return sum(term[0] for term in terms), sum(term[1] for term in terms)


def _expanded_term(constant: int, coefficient: int, *, first: bool) -> str:
    if bool(constant) == bool(coefficient):
        raise UnsupportedCondition("expanded term is ambiguous")
    value = coefficient if coefficient else constant
    text = _render_x(coefficient) if coefficient else str(constant)
    return text if first or value < 0 else f"+{text}"


def _expand_side(side: str) -> tuple[int, int, str]:
    """Expand one distributive-product side without simplifying like terms."""

    constant = coefficient = 0
    rendered: list[str] = []
    position = 0
    while position < len(side):
        parenthesized = _PARENTHESIZED_TERM.match(side, position)
        if parenthesized is not None:
            inner_terms = _simple_terms(parenthesized.group("inner"))
            if len(inner_terms) != 2 or not any(term[0] for term in inner_terms) or not any(term[1] for term in inner_terms):
                raise UnsupportedCondition("parentheses must contain one integer and one x-term")
            multiplier = int(parenthesized.group("multiplier"))
            for inner_constant, inner_coefficient in inner_terms:
                expanded_constant = multiplier * inner_constant
                expanded_coefficient = multiplier * inner_coefficient
                constant += expanded_constant
                coefficient += expanded_coefficient
                rendered.append(
                    _expanded_term(
                        expanded_constant, expanded_coefficient, first=not rendered
                    )
                )
            position = parenthesized.end()
            continue

        simple = _TERM.match(side, position)
        if simple is None:
            raise UnsupportedCondition("side contains unsupported terms")
        simple_constant, simple_coefficient = _term_values(simple.group(0))
        constant += simple_constant
        coefficient += simple_coefficient
        rendered.append(
            _expanded_term(simple_constant, simple_coefficient, first=not rendered)
        )
        position = simple.end()

    if coefficient == 0:
        raise UnsupportedCondition("each side must contain a nonzero x-term")
    return constant, coefficient, "".join(rendered)


def _render_x(coefficient: int) -> str:
    if coefficient == 1:
        return "x"
    if coefficient == -1:
        return "-x"
    return f"{coefficient}x"


def _render_difference(first: int, second: int, *, variable: bool = False) -> str:
    render = _render_x if variable else str
    if second >= 0:
        return f"{render(first)}-{render(second)}"
    return f"{render(first)}+{render(-second)}"


def _fraction_latex(numerator: int, denominator: int) -> str:
    """Render a signed fraction without reducing an equivalent fraction."""

    sign = "-" if numerator < 0 else ""
    return rf"{sign}\frac{{{abs(numerator)}}}{{{denominator}}}"


def _terminal_x_steps(value: Fraction, answer: str) -> str:
    """Show the exact fraction and its conversion to a decimal answer.

    A terminating decimal is formed by bringing the reduced denominator to the
    least applicable power of ten: 10, 100, or 1000.
    """

    if value.denominator == 1:
        return f"x={answer}"

    places = terminating_decimal_places(value)
    if places is None or places > 3:
        raise UnsupportedCondition("answer needs more than three decimal places")

    power_of_ten = 10**places
    fraction = _fraction_latex(value.numerator, value.denominator)
    decimal = answer.replace(",", "{,}")
    if value.denominator == power_of_ten:
        return f"x={fraction}={decimal}"

    scaled_numerator = value.numerator * power_of_ten // value.denominator
    scaled_fraction = _fraction_latex(scaled_numerator, power_of_ten)
    return f"x={fraction}={scaled_fraction}={decimal}"


def _parse_formula(formula: str) -> tuple[int, int, int, int, str | None]:
    if formula.count("=") != 1:
        raise UnsupportedCondition("equation must contain one equals sign")
    left, right = formula.split("=", 1)
    if "(" not in formula and ")" not in formula:
        left_constant, left_coefficient = _parse_side(left)
        right_constant, right_coefficient = _parse_side(right)
        return left_constant, left_coefficient, right_constant, right_coefficient, None

    if ("(" in left) != (")" in left) or ("(" in right) != (")" in right):
        raise UnsupportedCondition("parentheses are unmatched")
    if "(" in left:
        left_constant, left_coefficient, expanded_left = _expand_side(left)
    else:
        left_constant, left_coefficient = _parse_affine_side(left)
        expanded_left = left
    if "(" in right:
        right_constant, right_coefficient, expanded_right = _expand_side(right)
    else:
        right_constant, right_coefficient = _parse_affine_side(right)
        expanded_right = right
    return (
        left_constant,
        left_coefficient,
        right_constant,
        right_coefficient,
        f"{expanded_left}={expanded_right}",
    )


def _build_plan(formula: str) -> RepairPlan:
    (
        left_constant,
        left_coefficient,
        right_constant,
        right_coefficient,
        expanded,
    ) = _parse_formula(formula)
    coefficient = left_coefficient - right_coefficient
    constant = right_constant - left_constant
    if coefficient == 0:
        raise UnsupportedCondition("equation does not have one unique root")

    try:
        result = Fraction(constant, coefficient)
        answer = format_answer(result)
    except NumberFormatError as error:
        raise UnsupportedCondition("answer is not a terminating decimal") from error

    moved = (
        f"{_render_difference(left_coefficient, right_coefficient, variable=True)}="
        f"{_render_difference(right_constant, left_constant)}"
    )
    collected = f"{_render_x(coefficient)}={constant}"
    terminal_steps = _terminal_x_steps(result, answer)
    solution = (
        f"<p>{_SOLUTION_INTRO}</p>"
        f'<center><p><span data-inline-latex="{formula}'
        f'{f"\\iff {expanded}" if expanded is not None else ""}\\iff {moved}\\iff '
        f'{collected}\\iff {terminal_steps}"></span>.</p></center>'
    )
    condition = (
        f'<p>{_CONDITION_INTRO} '
        f'<span data-inline-latex="{formula}"></span>.</p>'
    )
    return RepairPlan(
        answer=answer,
        condition_html=condition,
        solution_html=solution,
    )


def build_repair_plan(formula: str) -> RepairPlan:
    """Build the parent-style plan for one supported linear equation."""

    return _build_plan(re.sub(r"\s+", "", formula))


def _condition_formula(condition: dict[str, Any]) -> str:
    soup = BeautifulSoup(str(condition.get("html") or ""), "html.parser")
    for tag in soup.find_all(True):
        allowed = {"p": set(), "span": {"data-inline-latex"}}.get(tag.name)
        if allowed is None or set(tag.attrs) != allowed:
            raise UnsupportedCondition("condition contains unsupported markup")

    spans = soup.find_all("span")
    if (
        len(spans) != 1
        or spans[0].get_text("", strip=True)
        or spans[0].parent.name != "p"
    ):
        raise UnsupportedCondition("condition equation markup is ambiguous")

    formula = re.sub(r"\s+", "", str(spans[0].get("data-inline-latex") or ""))
    spans[0].replace_with(formula)
    visible = soup.get_text(" ", strip=True).replace("\u00ad", "")
    visible = re.sub(r"\s+([.])", r"\1", " ".join(visible.split()))
    if visible not in {
        f"Найдите корень уравнения {formula}",
        f"Найдите корень уравнения {formula}.",
    }:
        raise UnsupportedCondition("condition wording does not match group 509214")
    return formula


def _answer_matches(section: dict[str, Any] | None, expected: str) -> bool:
    if section is None:
        return False
    text = BeautifulSoup(str(section.get("html") or ""), "html.parser").get_text(
        "", strip=True
    )
    try:
        return parse_rational(text) == parse_rational(expected)
    except (NumberFormatError, ValueError):
        return False


def build_context_repair_plan(context: dict[str, Any]) -> RepairPlan:
    """Build minimal transformations from one schema-v3 normalized context."""

    content = context.get("normalized_content")
    if (
        not isinstance(content, dict)
        or content.get("format") != "teacherhelper-normalized"
        or content.get("schema_version") != 3
        or content.get("assets") not in (None, [])
    ):
        raise UnsupportedCondition("assetless schema-v3 normalized content is required")

    condition = _section(content, "condition")
    answer = _section(content, "answer")
    solution = _section(content, "solution")
    if condition is None or tuple(condition.get("asset_keys") or ()):
        raise UnsupportedCondition("canonical assetless condition is required")

    formula = _condition_formula(condition)
    planned = build_repair_plan(formula)
    transformations: list[dict[str, Any]] = []

    if str(condition.get("html") or "") != planned.condition_html:
        transformations.append(
            _rewrite(condition, "condition", "Условие", planned.condition_html)
        )
    if solution is None or str(solution.get("html") or "") != planned.solution_html:
        transformations.append(
            _rewrite(solution, "solution", "Решение", planned.solution_html)
        )
    if not _answer_matches(answer, planned.answer):
        transformations.append(
            _rewrite(
                answer,
                "answer",
                "Ответ",
                f'<p><span data-effect="spaced">{planned.answer}</span></p>',
            )
        )

    return RepairPlan(
        answer=planned.answer,
        condition_html=planned.condition_html,
        solution_html=planned.solution_html,
        transformations=tuple(transformations),
    )
