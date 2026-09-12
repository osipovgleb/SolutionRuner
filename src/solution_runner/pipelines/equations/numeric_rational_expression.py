"""Planner for short numeric rational expressions with one outer operation."""

from __future__ import annotations

from fractions import Fraction
from math import gcd
import re
from typing import Any

from bs4 import BeautifulSoup

from ..triangles.isosceles.planner import _normalized_content, _section, _section_transformation
from ..triangles.right.planner import RepairPlan, RightTrianglePlanError


_RULE = "numeric-rational-expression-mixed-decimal"
_TERM = r"-?(?:\d+\\frac\{\d+\}\{\d+\}|\\frac\{\d+\}\{\d+\}|\d+(?:\{,\}\d+)?)"
_EXPRESSION = re.compile(
    rf"^\((?P<left>{_TERM})(?P<inner>[+-])(?P<right>{_TERM})\)"
    rf"(?P<outer>\\cdot|\\colon|\\div)(?P<factor>{_TERM})$"
)
_MIXED = re.compile(r"(?P<whole>\d+)\\frac\{(?P<numerator>\d+)\}\{(?P<denominator>\d+)\}$")
_FRACTION = re.compile(r"\\frac\{(?P<numerator>\d+)\}\{(?P<denominator>\d+)\}$")


class _ExpressionParser:
    """Parse the small, numeric-only LaTeX language used by this group."""

    def __init__(self, formula: str) -> None:
        self.formula = formula
        self.index = 0

    def parse(self) -> tuple[Any, ...]:
        node = self._sum()
        if self.index != len(self.formula):
            raise RightTrianglePlanError("condition does not match a registered numeric rational expression")
        return node

    def _sum(self) -> tuple[Any, ...]:
        node = self._product()
        while self._peek() in ("+", "-"):
            operation = self.formula[self.index]
            self.index += 1
            node = (operation, node, self._product())
        return node

    def _product(self) -> tuple[Any, ...]:
        node = self._unary()
        while True:
            if self.formula.startswith("\\cdot", self.index):
                self.index += len("\\cdot")
                node = ("\\cdot", node, self._unary())
            elif self.formula.startswith("\\colon", self.index):
                self.index += len("\\colon")
                node = ("\\colon", node, self._unary())
            else:
                return node

    def _unary(self) -> tuple[Any, ...]:
        if self._peek() == "-":
            self.index += 1
            return ("neg", self._unary())
        return self._primary()

    def _primary(self) -> tuple[Any, ...]:
        if self._peek() == "(":
            self.index += 1
            node = self._sum()
            if self._peek() != ")":
                raise RightTrianglePlanError("condition does not match a registered numeric rational expression")
            self.index += 1
            return ("group", node)
        if self.formula.startswith("\\frac", self.index):
            self.index += len("\\frac")
            return ("frac", _ExpressionParser(self._braced()).parse(), _ExpressionParser(self._braced()).parse())
        mixed = re.match(r"\d+\\frac\{\d+\}\{\d+\}", self.formula[self.index:])
        if mixed is not None:
            raw = mixed.group(0)
            self.index += len(raw)
            return ("number", _number(raw), raw)
        match = re.match(r"\d+(?:\{,\}\d+)?", self.formula[self.index:])
        if match is None:
            raise RightTrianglePlanError("condition does not match a registered numeric rational expression")
        raw = match.group(0)
        self.index += len(raw)
        return ("number", Fraction(raw.replace("{,}", ".")), raw)

    def _braced(self) -> str:
        if self._peek() != "{":
            raise RightTrianglePlanError("condition does not match a registered numeric rational expression")
        start = self.index = self.index + 1
        depth = 1
        while self.index < len(self.formula) and depth:
            if self.formula[self.index] == "{":
                depth += 1
            elif self.formula[self.index] == "}":
                depth -= 1
            self.index += 1
        if depth:
            raise RightTrianglePlanError("condition does not match a registered numeric rational expression")
        return self.formula[start:self.index - 1]

    def _peek(self) -> str:
        return self.formula[self.index:self.index + 1]


def _expression_value(node: tuple[Any, ...]) -> Fraction:
    match node:
        case ("number", value, _):
            return value
        case ("group", child):
            return _expression_value(child)
        case ("neg", child):
            return -_expression_value(child)
        case ("frac", numerator, denominator):
            divisor = _expression_value(denominator)
            if not divisor:
                raise RightTrianglePlanError("division by zero")
            return _expression_value(numerator) / divisor
        case (operation, left, right) if operation in ("+", "-", "\\cdot", "\\colon"):
            left_value, right_value = _expression_value(left), _expression_value(right)
            if operation == "+":
                return left_value + right_value
            if operation == "-":
                return left_value - right_value
            if operation == "\\cdot":
                return left_value * right_value
            if not right_value:
                raise RightTrianglePlanError("division by zero")
            return left_value / right_value
    raise RightTrianglePlanError("condition does not match a registered numeric rational expression")


def _expression_latex(node: tuple[Any, ...], *, computed: bool = False) -> str:
    if computed and node[0] not in ("number",):
        return _fraction_latex(_expression_value(node))
    match node:
        case ("number", _, raw):
            return raw
        case ("group", child):
            return f"({_expression_latex(child)})"
        case ("neg", child):
            return f"-{_expression_latex(child)}"
        case ("frac", numerator, denominator):
            return f"\\frac{{{_expression_latex(numerator)}}}{{{_expression_latex(denominator)}}}"
        case (operation, left, right) if operation in ("+", "-", "\\cdot", "\\colon"):
            return f"{_expression_latex(left, computed=left[0] not in ('number', 'frac'))}{operation}{_expression_latex(right, computed=right[0] not in ('number', 'frac'))}"
    raise RightTrianglePlanError("condition does not match a registered numeric rational expression")


def _expression_steps(node: tuple[Any, ...]) -> list[str]:
    match node:
        case ("number", _, _):
            return []
        case ("group", child) | ("neg", child):
            return _expression_steps(child)
        case ("frac", numerator, denominator):
            steps = _expression_steps(numerator) + _expression_steps(denominator)
            if numerator[0] not in ("number", "frac") or denominator[0] not in ("number", "frac"):
                steps.append(f"{_expression_latex(node)}={_fraction_latex(_expression_value(node))}")
            return steps
        case (operation, left, right) if operation in ("+", "-", "\\cdot", "\\colon"):
            steps = _expression_steps(left) + _expression_steps(right)
            steps.append(
                f"{_expression_latex(left, computed=left[0] not in ('number', 'frac'))}"
                f"{operation}{_expression_latex(right, computed=right[0] not in ('number', 'frac'))}"
                f"={_fraction_latex(_expression_value(node))}"
            )
            return steps
    raise RightTrianglePlanError("condition does not match a registered numeric rational expression")


def _number(value: str) -> Fraction:
    sign = -1 if value.startswith("-") else 1
    raw = value.removeprefix("-")
    if match := _MIXED.fullmatch(raw):
        result = Fraction(int(match["whole"])) + Fraction(
            int(match["numerator"]), int(match["denominator"])
        )
    elif match := _FRACTION.fullmatch(raw):
        result = Fraction(int(match["numerator"]), int(match["denominator"]))
    else:
        result = Fraction(raw.replace("{,}", "."))
    return sign * result


def _latex(value: Fraction) -> str:
    if value.denominator == 1:
        return str(value.numerator)
    return f"{'-' if value < 0 else ''}\\frac{{{abs(value.numerator)}}}{{{value.denominator}}}"


def _fraction_latex(value: Fraction) -> str:
    """Render a value explicitly as a fraction, including a denominator of one."""

    return f"{'-' if value < 0 else ''}\\frac{{{abs(value.numerator)}}}{{{value.denominator}}}"


def _source_fraction_latex(value: str) -> str:
    """Show the first mandatory conversion without silently simplifying it."""

    sign = "-" if value.startswith("-") else ""
    raw = value.removeprefix("-")
    if match := _MIXED.fullmatch(raw):
        numerator = int(match["whole"]) * int(match["denominator"]) + int(match["numerator"])
        return f"{sign}\\frac{{{numerator}}}{{{match['denominator']}}}"
    if _FRACTION.fullmatch(raw):
        return value
    if "{,}" in raw:
        whole, fractional = raw.split("{,}", 1)
        return f"{sign}\\frac{{{int(whole + fractional)}}}{{{10 ** len(fractional)}}}"
    return f"{sign}\\frac{{{raw}}}{{1}}"


def _common_denominator_row(left: Fraction, right: Fraction, operator: str) -> tuple[str, Fraction]:
    denominator = left.denominator * right.denominator
    # The groups use small denominators.  This avoids importing a second math engine
    # while retaining the actual least common denominator in the written solution.
    from math import lcm

    denominator = lcm(left.denominator, right.denominator)
    left_numerator = left.numerator * (denominator // left.denominator)
    right_numerator = right.numerator * (denominator // right.denominator)
    row = (
        f"\\frac{{{left_numerator}}}{{{denominator}}}{operator}"
        f"\\frac{{{right_numerator}}}{{{denominator}}}"
    )
    return row, Fraction(left_numerator + right_numerator if operator == "+" else left_numerator - right_numerator, denominator)


def _answer(value: Fraction) -> str:
    denominator = value.denominator
    twos = fives = 0
    while denominator % 2 == 0:
        denominator //= 2
        twos += 1
    while denominator % 5 == 0:
        denominator //= 5
        fives += 1
    if denominator != 1:
        raise RightTrianglePlanError("result is not a terminating decimal")
    if value.denominator == 1:
        return str(value.numerator)
    digits = max(twos, fives)
    raw = str(abs(value.numerator) * 10**digits // value.denominator).zfill(digits + 1)
    return f"{'-' if value < 0 else ''}{raw[:-digits]},{raw[-digits:]}"


def _answer_latex(value: Fraction) -> str:
    """Use the answer representation in the last row of the calculation."""

    return _answer(value).replace(",", "{,}")


def _formula(condition: dict[str, Any]) -> str:
    soup = BeautifulSoup(str(condition.get("html") or ""), "html.parser")
    formulas = soup.find_all("span", attrs={"data-inline-latex": True})
    if len(formulas) != 1:
        raise RightTrianglePlanError("condition must contain one formula")
    formula = (
        str(formulas[0].get("data-inline-latex") or "")
        .replace("\\left", "")
        .replace("\\right", "")
        .replace(":", "\\colon")
        .replace(" ", "")
    )
    return formula


def _generic_plan(
    *,
    formula: str,
    answer_section: dict[str, Any] | None,
    solution_section: dict[str, Any] | None,
) -> RepairPlan:
    expression = _ExpressionParser(formula).parse()
    result = _expression_value(expression)
    answer = _answer(result)
    rows = _expression_steps(expression)
    if not rows:
        raise RightTrianglePlanError("condition does not match a registered numeric rational expression")
    calculation = "".join(
        f'<center><p><span data-inline-latex="{row}"></span>.</p></center>'
        for row in rows
    )
    expected_solution = (
        "<p>Выполним действия по порядку:</p>"
        f"{calculation}"
        f'<p>Следовательно, значение выражения равно <span data-inline-latex="{_answer_latex(result)}"></span>.</p>'
    )
    changes: list[dict[str, Any]] = []
    if solution_section is None or str(solution_section.get("html") or "") != expected_solution:
        changes.append(_section_transformation(solution_section, "solution", "Решение", expected_solution))
    current_answer = BeautifulSoup(
        str(answer_section.get("html") or "") if answer_section else "", "html.parser"
    ).get_text("", strip=True).replace(" ", "")
    if current_answer != answer:
        changes.append(
            _section_transformation(
                answer_section, "answer", "Ответ", f'<p><span data-effect="spaced">{answer}</span></p>'
            )
        )
    return RepairPlan(answer=answer, transformations=tuple(changes))


def build_context_repair_plan(context: dict[str, Any]) -> RepairPlan:
    """Build a transparent three-step calculation for one audited expression."""

    content = _normalized_content(context)
    condition = _section(content, "condition")
    answer_section = _section(content, "answer")
    solution_section = _section(content, "solution")
    if condition is None or content.get("assets") or tuple(condition.get("asset_keys") or ()):
        raise RightTrianglePlanError("numeric expression conditions must be text-only")

    formula = _formula(condition)
    match = _EXPRESSION.fullmatch(formula)
    if match is None:
        return _generic_plan(
            formula=formula,
            answer_section=answer_section,
            solution_section=solution_section,
        )
    left, right, factor = (_number(match[name]) for name in ("left", "right", "factor"))
    common_row, inner = _common_denominator_row(left, right, match["inner"])
    if match["outer"] == "\\cdot":
        result = inner * factor
        outer_latex = "\\cdot"
    else:
        if factor == 0:
            raise RightTrianglePlanError("division by zero")
        result = inner / factor
        outer_latex = "\\colon"

    answer = _answer(result)
    converted_left = _source_fraction_latex(match["left"])
    converted_right = _source_fraction_latex(match["right"])
    converted_factor = _source_fraction_latex(match["factor"])
    factor_fraction = _fraction_latex(factor)
    converted = f"({converted_left}{match['inner']}{converted_right}){outer_latex}{converted_factor}"
    inside = _latex(inner)
    common_step = f"({common_row}){outer_latex}{factor_fraction}"

    steps = [
        formula,
        converted,
        common_step,
        f"{inside}{outer_latex}{factor_fraction}",
    ]
    if match["outer"] != "\\cdot":
        reciprocal = f"\\frac{{{factor.denominator}}}{{{abs(factor.numerator)}}}"
        if factor < 0:
            reciprocal = "-" + reciprocal
        multiplication = f"{inside}\\cdot{reciprocal}"
        product_factor = Fraction(1, 1) / factor
        steps.append(multiplication)
    else:
        multiplication = f"{inside}\\cdot{factor_fraction}"
        product_factor = factor

    first_numerator, first_denominator = inner.numerator, inner.denominator
    second_numerator, second_denominator = product_factor.numerator, product_factor.denominator
    first_divisor = gcd(abs(first_numerator), abs(second_denominator))
    second_divisor = gcd(abs(second_numerator), abs(first_denominator))
    first_numerator //= first_divisor
    second_denominator //= first_divisor
    second_numerator //= second_divisor
    first_denominator //= second_divisor
    reduced_first = Fraction(first_numerator, first_denominator)
    reduced_second = Fraction(second_numerator, second_denominator)
    reduced_product = f"{_fraction_latex(reduced_first)}\\cdot{_fraction_latex(reduced_second)}"
    one_fraction = (
        f"\\frac{{{first_numerator}\\cdot{second_numerator}}}"
        f"{{{first_denominator}\\cdot{second_denominator}}}"
    )
    steps.extend((reduced_product, one_fraction, _answer_latex(result)))
    calculation = "=".join(steps)
    expected_solution = f'<center><p><span data-inline-latex="{calculation}"></span></p></center>'
    changes: list[dict[str, Any]] = []
    if solution_section is None or str(solution_section.get("html") or "") != expected_solution:
        changes.append(_section_transformation(solution_section, "solution", "Решение", expected_solution))
    current_answer = BeautifulSoup(
        str(answer_section.get("html") or "") if answer_section else "", "html.parser"
    ).get_text("", strip=True).replace(" ", "")
    if current_answer != answer:
        changes.append(
            _section_transformation(
                answer_section, "answer", "Ответ", f'<p><span data-effect="spaced">{answer}</span></p>'
            )
        )
    return RepairPlan(answer=answer, transformations=tuple(changes))
