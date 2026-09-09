r"""Deterministic repair plan for \log_a(b+cx)=d equations."""
from __future__ import annotations

import re
from fractions import Fraction
from typing import Any

from bs4 import BeautifulSoup

from solution_runner.pipelines.core.numbers import NumberFormatError, format_answer, format_latex_fraction, parse_rational
from solution_runner.pipelines.equations.group_26650 import _answer_steps, _linear_latex, _parse_linear, _rewrite, _section
from solution_runner.pipelines.equations.group_26656 import RepairPlan

RULE = "logarithm-common-normalized"
_BASE = r"(?:[2-9]|[1-9]\d+)"
_FRACTION_BASE = r"\\frac\{[1-9]\d*\}\{[1-9]\d*\}"
_POLYNOMIAL_ARGUMENT = r"(?:[^{}]|\{2\})+"
_FORMULA = re.compile(
    rf"\\log_(?P<base>\{{(?:\(?{_BASE}\)?|\(?{_FRACTION_BASE}\)?)\}}|\(?{_BASE}\)?)"
    r"\s*\((?P<inner>[^{}]+)\)=(?P<right>-?\d+)"
)
_EQUAL_LOGARITHMS = re.compile(
    rf"\\log_(?P<left_base>\{{?\(?{_BASE}\)?\}}?)\s*\((?P<left_inner>{_POLYNOMIAL_ARGUMENT})\)\s*="
    rf"\\log_(?P<right_base>\{{?\(?{_BASE}\)?\}}?)"
    rf"(?:\s*\((?P<right_parenthesized>{_POLYNOMIAL_ARGUMENT})\)|\s+(?P<right_bare>[^\s{{}}]+))"
)
_MULTIPLIED_LOGARITHM = re.compile(
    rf"\\log_(?P<left_base>\{{?\(?{_BASE}\)?\}}?)\s*\((?P<left_inner>[^{{}}]+)\)\s*="
    rf"(?P<multiplier>[1-9]\d*)\\log_(?P<right_base>\{{?\(?{_BASE}\)?\}}?)\s*(?P<right_argument>[1-9]\d*)"
)
_PARENTHESIZED_BASE = re.compile(rf"\\log_\{{\((?P<base>{_BASE}|{_FRACTION_BASE})\)\}}")
_DECIMAL_LOGARITHM = re.compile(r"\\lg(?=\s*\()")


class UnsupportedCondition(ValueError):
    pass


def _parse_affine(value: str) -> tuple[int, int]:
    """Parse a linear logarithm argument, including a constant one."""

    if re.fullmatch(r"-?\d+", value):
        return int(value), 0
    return _parse_linear(value)


def _parse_quadratic(value: str) -> tuple[int, int, int]:
    """Parse an integer polynomial of degree at most two in a fixed grammar."""

    text = value.replace(" ", "")
    if not text:
        raise UnsupportedCondition("empty logarithm argument")
    terms = re.findall(r"[+-]?[^+-]+", text)
    if "".join(terms) != text:
        raise UnsupportedCondition("quadratic logarithm argument is unsupported")
    square = linear = constant = 0
    for term in terms:
        sign = -1 if term.startswith("-") else 1
        body = term.lstrip("+-")
        if body.endswith("x^{2}"):
            factor = body[:-5]
            coefficient = 1 if not factor else int(factor)
            square += sign * coefficient
        elif body.endswith("x"):
            factor = body[:-1]
            coefficient = 1 if not factor else int(factor)
            linear += sign * coefficient
        elif re.fullmatch(r"\d+", body):
            constant += sign * int(body)
        else:
            raise UnsupportedCondition("quadratic logarithm argument is unsupported")
    return square, linear, constant


def _parse_logarithm_base(token: str) -> Fraction:
    """Remove only outer TeX grouping before parsing an exact base."""

    value = token
    if value.startswith("{") and value.endswith("}"):
        value = value[1:-1]
    if value.startswith("(") and value.endswith(")"):
        value = value[1:-1]
    try:
        result = parse_rational(value)
    except NumberFormatError as error:
        raise UnsupportedCondition("logarithm base is unsupported") from error
    if result <= 0 or result == 1:
        raise UnsupportedCondition("logarithm base must be positive and different from one")
    return result


def _normalize_parenthesized_log_base(match: re.Match[str]) -> str:
    """Remove redundant brackets around a numeric or fractional base."""

    base = match.group("base")
    return f"\\log_{{{base}}}" if base.startswith("\\frac") else f"\\log_{base}"


def _log_base_latex(base: Fraction | int) -> str:
    """Keep a multi-digit logarithm base inside one TeX subscript."""

    value = Fraction(base)
    if value.denominator != 1:
        return f"{{{format_latex_fraction(value)}}}"
    return str(value.numerator) if value.numerator < 10 else f"{{{value.numerator}}}"


def _positive_affine_condition(constant: int, coefficient: int) -> str:
    """Move only the constant when recording a parent-style positivity check."""

    variable = _linear_latex(0, coefficient)
    if constant < 0:
        return f"{variable}>{-constant}"
    if constant > 0:
        return f"{variable}+{constant}>0"
    return f"{variable}>0"


def _solution_signature(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for span in soup.find_all("span", attrs={"data-inline-latex": True}):
        span["data-inline-latex"] = re.sub(r"\s+", "", str(span["data-inline-latex"])).replace("ё", "е")
    normalized = str(soup).replace("\u00ad", "")
    normalized = re.sub(r">\s+<", "><", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def _build_plan(formula: str) -> RepairPlan:
    # ``\\lg`` is the conventional shorthand for ``\\log_{10}`` in source tasks.
    # Normalize only for calculation; the condition itself is kept untouched.
    formula = _DECIMAL_LOGARITHM.sub(r"\\log_{10}", formula)
    multiplied_log = _MULTIPLIED_LOGARITHM.fullmatch(formula)
    if multiplied_log:
        left_base = int(multiplied_log.group("left_base").strip("{}()"))
        right_base = int(multiplied_log.group("right_base").strip("{}()"))
        if left_base != right_base:
            raise UnsupportedCondition("logarithm bases must match")
        left_inner = multiplied_log.group("left_inner")
        constant, coefficient = _parse_affine(left_inner)
        if coefficient == 0:
            raise UnsupportedCondition("logarithm argument must contain x")
        multiplier = int(multiplied_log.group("multiplier"))
        right_argument = int(multiplied_log.group("right_argument"))
        value = right_argument**multiplier
        result = Fraction(value - constant, coefficient)
        if constant + coefficient * result <= 0:
            raise UnsupportedCondition("logarithm argument must be positive")
        try:
            answer = format_answer(result)
        except NumberFormatError as error:
            raise UnsupportedCondition("answer does not terminate") from error
        left_base_latex = _log_base_latex(left_base)
        right_base_latex = _log_base_latex(right_base)
        log_left = f"\\log_{left_base_latex} ({left_inner})"
        log_right = f"\\log_{right_base_latex} {right_argument}^{{{multiplier}}}"
        solution = (
            "<p>Последовательно получаем:</p>"
            f'<center><p><span data-inline-latex="{log_left}={multiplier}\\log_{right_base_latex} {right_argument}'
            f'\\iff {log_left}={log_right}\\iff {left_inner}={value}\\iff {_answer_steps(result)}"></span>.</p></center>'
        )
        return RepairPlan(answer=answer, condition_html="", solution_html=solution)
    equal_logs = _EQUAL_LOGARITHMS.fullmatch(formula)
    if equal_logs:
        left_base = int(equal_logs.group("left_base").strip("{}()"))
        right_base = int(equal_logs.group("right_base").strip("{}()"))
        if left_base != right_base:
            raise UnsupportedCondition("logarithm bases must match")
        left_inner = equal_logs.group("left_inner")
        right_inner = str(
            equal_logs.group("right_parenthesized") or equal_logs.group("right_bare") or ""
        )
        try:
            left_constant, left_coefficient = _parse_affine(left_inner)
            right_constant, right_coefficient = _parse_affine(right_inner)
        except ValueError:
            left_square, left_coefficient, left_constant = _parse_quadratic(left_inner)
            right_square, right_coefficient, right_constant = _parse_quadratic(right_inner)
            if left_square != right_square:
                raise UnsupportedCondition("quadratic terms do not cancel")
            coefficient = left_coefficient - right_coefficient
            if coefficient == 0:
                raise UnsupportedCondition("logarithm arguments do not determine x")
            result = Fraction(right_constant - left_constant, coefficient)
            right_value = (
                right_square * result * result + right_coefficient * result + right_constant
            )
            if right_value <= 0:
                raise UnsupportedCondition("logarithm arguments must be positive")
            try:
                answer = format_answer(result)
            except NumberFormatError as error:
                raise UnsupportedCondition("answer does not terminate") from error
            left_base_latex = _log_base_latex(left_base)
            right_base_latex = _log_base_latex(right_base)
            solution = (
                "<p>Перейдем к одному основанию степени:</p>"
                f'<center><p><span data-inline-latex="\\log_{left_base_latex} ({left_inner})='
                f'\\log_{right_base_latex} ({right_inner})\\iff '
                f'\\begin{{cases}}{left_inner}={right_inner}\\\\{right_inner}\\gt 0\\end{{cases}}.\\quad '
                f'\\iff x={format_latex_fraction(result)}"></span>.</p></center>'
            )
            return RepairPlan(answer=answer, condition_html="", solution_html=solution)
        coefficient = left_coefficient - right_coefficient
        if coefficient == 0:
            raise UnsupportedCondition("logarithm arguments do not determine x")
        result = Fraction(right_constant - left_constant, coefficient)
        left_value = left_constant + left_coefficient * result
        right_value = right_constant + right_coefficient * result
        if left_value <= 0 or right_value <= 0:
            raise UnsupportedCondition("logarithm arguments must be positive")
        try:
            answer = format_answer(result)
        except NumberFormatError as error:
            raise UnsupportedCondition("answer does not terminate") from error
        log_left = f"\\log_{_log_base_latex(left_base)} ({left_inner})"
        log_right = (
            f"\\log_{_log_base_latex(right_base)} ({right_inner})"
            if equal_logs.group("right_parenthesized") is not None
            else f"\\log_{_log_base_latex(right_base)} {right_inner}"
        )
        if right_coefficient != 0:
            positivity = _positive_affine_condition(right_constant, right_coefficient)
            exact = format_latex_fraction(result)
            solution = (
                "<p>Логарифмы двух выражений равны, если сами выражения равны и при этом положительны:</p>"
                f'<center><p><span data-inline-latex="{log_left}={log_right}\\iff '
                f'\\begin{{cases}}{left_inner}={right_inner}\\\\{right_inner}>0\\end{{cases}}.\\quad '
                f'\\iff \\begin{{cases}}x={exact}\\\\{positivity}\\end{{cases}}.\\quad '
                f'\\iff {_answer_steps(result)}"></span>.</p></center>'
            )
            return RepairPlan(answer=answer, condition_html="", solution_html=solution)
        solution = (
            "<p>Последовательно получаем:</p>"
            f'<center><p><span data-inline-latex="{log_left}={log_right}\\iff '
            f'{left_inner}={right_inner}\\iff {_answer_steps(result)}"></span>.</p></center>'
        )
        return RepairPlan(answer=answer, condition_html="", solution_html=solution)
    match = _FORMULA.fullmatch(re.sub(r"\s+", "", formula))
    if not match:
        raise UnsupportedCondition("unsupported logarithmic equation")
    base = _parse_logarithm_base(match.group("base"))
    power = int(match.group("right"))
    constant, coefficient = _parse_linear(match.group("inner"))
    if coefficient == 0:
        raise UnsupportedCondition("logarithm argument must contain x")
    value = base**power
    result = Fraction(value - constant, coefficient)
    try:
        answer = format_answer(result)
    except NumberFormatError as error:
        raise UnsupportedCondition("answer does not terminate") from error
    inner = match.group("inner")
    base_latex = format_latex_fraction(base)
    power_base = f"({base_latex})" if base.denominator != 1 else base_latex
    log = f"\\log_{_log_base_latex(base)} ({inner})={power}"
    solution = (
        "<p>Последовательно получаем:</p>"
        f'<center><p><span data-inline-latex="{log}\\iff {inner}={power_base}^{{{power}}}\\iff {inner}={format_latex_fraction(value)}\\iff {_answer_steps(result)}"></span>.</p></center>'
    )
    return RepairPlan(answer=answer, condition_html="", solution_html=solution)


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
    source_formula = str(spans[0].get("data-inline-latex") or "")
    if "\\log_" not in source_formula and "\\lg" not in source_formula:
        raise UnsupportedCondition("condition is not logarithmic")
    spans[0].replace_with(source_formula)
    canonical_formula = _PARENTHESIZED_BASE.sub(_normalize_parenthesized_log_base, source_formula)
    planned = _build_plan(canonical_formula)
    changes = []
    if canonical_formula != source_formula:
        canonical_html = str(condition.get("html") or "").replace(source_formula, canonical_formula)
        changes.append(_rewrite(condition, "condition", "Условие", canonical_html))
    if solution is None or _solution_signature(str(solution.get("html") or "")) != _solution_signature(planned.solution_html):
        changes.append(_rewrite(solution, "solution", "Решение", planned.solution_html))
    current = BeautifulSoup(str(answer.get("html") or "") if answer else "", "html.parser").get_text("", strip=True).replace(" ", "")
    if current != planned.answer:
        changes.append(_rewrite(answer, "answer", "Ответ", f'<p><span data-effect="spaced">{planned.answer}</span></p>'))
    return RepairPlan(answer=planned.answer, condition_html=canonical_html if canonical_formula != source_formula else str(condition.get("html") or ""), solution_html=planned.solution_html, transformations=tuple(changes))
