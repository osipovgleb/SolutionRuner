"""Deterministic planners for two parent-approved rational-expression forms."""

from __future__ import annotations

from fractions import Fraction
from collections import Counter
from math import gcd, isqrt
import re
from typing import Any

from bs4 import BeautifulSoup
from solution_runner.pipelines.core.numbers import parse_rational

from ..triangles.isosceles.planner import _normalized_content, _section, _section_transformation
from ..triangles.right.planner import RepairPlan, RightTrianglePlanError


_SQUARE_DIFFERENCE = re.compile(
    r"^\((?P<left>\d+)\^\{2\}-(?P<right>\d+)\^\{2\}\)\\colon(?P<divisor>\d+)$"
)
_FRACTION_DIVISION = re.compile(
    r"^(?:(?P<whole>\d+)\\frac\{(?P<numerator>\d+)\}\{(?P<denominator>\d+)\}"
    r"|\\frac\{(?P<first_numerator>\d+)\}\{(?P<first_denominator>\d+)\})"
    r"(?P<operation>\\colon|\\cdot)\\frac\{(?P<divisor_numerator>\d+)\}\{(?P<divisor_denominator>\d+)\}$"
)
_CONJUGATE_PRODUCT = re.compile(
    r"^\((?P<first>\\sqrt\{\d+\}|\d+)-(?P<second>\\sqrt\{\d+\}|\d+)\)"
    r"(?:\\cdot)?\((?P=first)\+(?P=second)\)$"
)
_RADICAL_FACTOR = re.compile(
    r"^\(\\sqrt\{(?P<left>\d+)\}(?P<sign>[+-])\\sqrt\{(?P<base>\d+)\}\)"
    r"(?:\\cdot)?\\sqrt\{(?P=base)\}$"
)


def _formula(condition: dict[str, Any]) -> str:
    soup = BeautifulSoup(str(condition.get("html") or ""), "html.parser")
    formulas = soup.find_all("span", attrs={"data-inline-latex": True})
    if len(formulas) != 1:
        raise RightTrianglePlanError("condition must contain one formula")
    return (
        str(formulas[0].get("data-inline-latex") or "")
        .replace("\\left", "")
        .replace("\\right", "")
        .replace("\\div", "\\colon")
        .replace(":", "\\colon")
        .replace(" ", "")
    )


def _fraction(value: Fraction) -> str:
    if value.denominator == 1:
        return str(value.numerator)
    return f"{'-' if value < 0 else ''}\\frac{{{abs(value.numerator)}}}{{{value.denominator}}}"


def _decimal(value: Fraction) -> str:
    remainder = value.denominator
    twos = fives = 0
    while remainder % 2 == 0:
        remainder //= 2
        twos += 1
    while remainder % 5 == 0:
        remainder //= 5
        fives += 1
    if remainder != 1:
        raise RightTrianglePlanError("result is not a terminating decimal")
    if value.denominator == 1:
        return str(value.numerator)
    digits = max(twos, fives)
    scaled = abs(value.numerator) * 10**digits // value.denominator
    rendered = str(scaled).zfill(digits + 1)
    return f"{'-' if value < 0 else ''}{rendered[:-digits]},{rendered[-digits:]}"


def _finish(value: Fraction) -> tuple[str, ...]:
    """Keep the ordinary fraction and explicitly show its decimal form."""

    if value.denominator == 1:
        return (str(value.numerator),)
    decimal = _decimal(value)
    digits = len(decimal.removeprefix("-").split(",", 1)[1])
    scale = 10**digits // value.denominator
    numerator = value.numerator * scale
    return (_fraction(value), f"\\frac{{{numerator}}}{{{10**digits}}}", decimal.replace(",", "{,}"))


def _plan(context: dict[str, Any], *, formula_pattern: re.Pattern[str], calculation: Any, vertical_roots: bool = False) -> RepairPlan:
    content = _normalized_content(context)
    condition = _section(content, "condition")
    answer_section = _section(content, "answer")
    solution_section = _section(content, "solution")
    if condition is None or content.get("assets") or tuple(condition.get("asset_keys") or ()):
        raise RightTrianglePlanError("numeric expression conditions must be text-only")
    formula = _formula(condition)
    match = formula_pattern.fullmatch(formula)
    if match is None:
        raise RightTrianglePlanError("condition does not match the registered expression form")
    steps, result = calculation(formula, match)
    answer = _decimal(result)
    calculation_html = "=".join((*steps, *_finish(result)))
    html = (
        '<p>Вы­пол­ним пре­об­ра­зо­ва­ния:</p><center><p>'
        f'<span data-inline-latex="{calculation_html}"></span>.</p></center>'
    )
    if vertical_roots:
        lines = (*steps, *_finish(result))
        html = (
            '<p>Упростим выражение, разложив подкоренные выражения на множители '
            'и вынесем за знак корня полные квадраты чисел:</p>'
            + ''.join(
                ('<p>Сгруппируем одинаковые корни и воспользуемся равенством '
                 '<span data-inline-latex="(\\sqrt{a})^{2}=a"></span> при '
                 '<span data-inline-latex="a\\geq0"></span>:</p>' if index == 3 else '')
                + f'<center><p><span data-inline-latex="{line if index == 0 else "=" + line}"></span>.</p></center>'
                for index, line in enumerate(lines)
            )
        )
    changes: list[dict[str, Any]] = []
    if solution_section is None or str(solution_section.get("html") or "") != html:
        changes.append(_section_transformation(solution_section, "solution", "Решение", html))
    current_answer = BeautifulSoup(
        str(answer_section.get("html") or "") if answer_section else "", "html.parser"
    ).get_text("", strip=True).replace(" ", "")
    if current_answer != answer:
        changes.append(_section_transformation(
            answer_section, "answer", "Ответ", f'<p><span data-effect="spaced">{answer}</span></p>'
        ))
    return RepairPlan(answer=answer, transformations=tuple(changes))


def build_square_difference_plan(context: dict[str, Any]) -> RepairPlan:
    """Use the difference-of-squares identity before division."""

    def calculation(formula: str, match: re.Match[str]) -> tuple[tuple[str, ...], Fraction]:
        left, right, divisor = (int(match[name]) for name in ("left", "right", "divisor"))
        difference, total = left - right, left + right
        result = Fraction(difference * total, divisor)
        return (
            formula,
            f"\\frac{{({left}-{right})({left}+{right})}}{{{divisor}}}",
            f"\\frac{{{difference}\\cdot{total}}}{{{divisor}}}",
        ), result

    return _plan(context, formula_pattern=_SQUARE_DIFFERENCE, calculation=calculation)


def build_fraction_division_plan(context: dict[str, Any]) -> RepairPlan:
    """Convert a mixed number if needed, reverse the divisor, then cancel."""

    def calculation(formula: str, match: re.Match[str]) -> tuple[tuple[str, ...], Fraction]:
        divisor_numerator = int(match["divisor_numerator"])
        divisor_denominator = int(match["divisor_denominator"])
        if match["whole"] is None:
            first = Fraction(int(match["first_numerator"]), int(match["first_denominator"]))
        else:
            whole, numerator, denominator = (int(match[name]) for name in ("whole", "numerator", "denominator"))
            first = Fraction(whole * denominator + numerator, denominator)
        second = Fraction(divisor_numerator, divisor_denominator)
        result = first / second if match["operation"] == "\\colon" else first * second
        left_numerator, left_denominator = first.numerator, first.denominator
        right_numerator, right_denominator = second.denominator, second.numerator
        if match["operation"] == "\\colon":
            right_numerator, right_denominator = second.denominator, second.numerator
        else:
            right_numerator, right_denominator = second.numerator, second.denominator
        divisor = gcd(left_numerator, right_denominator)
        left_numerator //= divisor
        right_denominator //= divisor
        divisor = gcd(right_numerator, left_denominator)
        right_numerator //= divisor
        left_denominator //= divisor
        return (
            formula,
            f"\\frac{{{first.numerator}}}{{{first.denominator}}}\\cdot\\frac{{{second.denominator}}}{{{second.numerator}}}",
            f"\\frac{{{left_numerator}}}{{{left_denominator}}}\\cdot\\frac{{{right_numerator}}}{{{right_denominator}}}",
            f"\\frac{{{left_numerator}\\cdot{right_numerator}}}{{{left_denominator}\\cdot{right_denominator}}}",
        ), result

    return _plan(context, formula_pattern=_FRACTION_DIVISION, calculation=calculation)


def _squared_value(token: str) -> int:
    radical = re.fullmatch(r"\\sqrt\{(?P<value>\d+)\}", token)
    if radical:
        return int(radical["value"])
    value = int(token)
    return value * value


def _squared_latex(token: str) -> str:
    return f"({token})^{{2}}" if token.startswith("\\sqrt") else f"{token}^{{2}}"


def build_conjugate_product_plan(context: dict[str, Any]) -> RepairPlan:
    """Apply the difference-of-squares formula to matching radical conjugates."""

    content = _normalized_content(context)
    condition = _section(content, "condition")
    if condition is not None and _RADICAL_FACTOR.fullmatch(_formula(condition)):
        return build_radical_factor_plan(context)

    def calculation(formula: str, match: re.Match[str]) -> tuple[tuple[str, ...], Fraction]:
        first, second = match["first"], match["second"]
        first_value, second_value = _squared_value(first), _squared_value(second)
        return (
            formula,
            f"{_squared_latex(first)}-{_squared_latex(second)}",
            f"{first_value}-{second_value}",
        ), Fraction(first_value - second_value)

    return _plan(context, formula_pattern=_CONJUGATE_PRODUCT, calculation=calculation)


def build_radical_factor_plan(context: dict[str, Any], *, vertical_roots: bool = False) -> RepairPlan:
    """Simplify a radical multiple before multiplying by the shared radical."""

    def calculation(formula: str, match: re.Match[str]) -> tuple[tuple[str, ...], Fraction]:
        left, base = int(match["left"]), int(match["base"])
        if left % base:
            raise RightTrianglePlanError("radicals do not have a shared square-free factor")
        coefficient = isqrt(left // base)
        if coefficient * coefficient * base != left:
            raise RightTrianglePlanError("first radical cannot be simplified to the shared radical")
        signed_coefficient = coefficient + (1 if match["sign"] == "+" else -1)
        if signed_coefficient == 0:
            middle = "0"
        elif signed_coefficient == 1:
            middle = f"\\sqrt{{{base}}}"
        elif signed_coefficient == -1:
            middle = f"-\\sqrt{{{base}}}"
        else:
            middle = f"{signed_coefficient}\\sqrt{{{base}}}"
        return (
            formula,
            f"({coefficient}\\sqrt{{{base}}}{match['sign']}\\sqrt{{{base}}})\\cdot\\sqrt{{{base}}}",
            f"{middle}\\cdot\\sqrt{{{base}}}",
            f"{signed_coefficient}\\cdot{base}",
        ), Fraction(signed_coefficient * base)

    return _plan(context, formula_pattern=_RADICAL_FACTOR, calculation=calculation, vertical_roots=vertical_roots)


# A product only: sums, quotients, variables and negative radicands fail closed.
_ROOT_TERM = r"(?:[1-9]\d{0,5})?\\sqrt\{[1-9]\d{0,5}\}"
_ROOT_PRODUCT = re.compile(rf"{_ROOT_TERM}(?:\\cdot{_ROOT_TERM}){{1,3}}")


def _prime_factors(value: int) -> Counter[int]:
    factors: Counter[int] = Counter()
    divisor = 2
    while divisor * divisor <= value:
        while value % divisor == 0:
            factors[divisor] += 1
            value //= divisor
        divisor += 1
    if value > 1:
        factors[value] += 1
    return factors


def build_root_product_plan(context: dict[str, Any]) -> RepairPlan:
    """Pair square roots after factoring, following parent 137285's method."""
    content = _normalized_content(context)
    condition = _section(content, "condition")
    soup = BeautifulSoup(str((condition or {}).get("html") or ""), "html.parser")
    for span in soup.select("span[data-inline-latex]"):
        span.replace_with("FORMULA")
    prose = " ".join(soup.get_text(" ", strip=True).replace("\u00ad", "").split())
    prose = re.sub(r"\s+\.", ".", prose)
    if prose not in {"Найдите значение выражения FORMULA.", "Найдите значение выражения FORMULA"}:
        raise RightTrianglePlanError("condition is not a plain numeric root product")
    if condition is not None and _RADICAL_FACTOR.fullmatch(_formula(condition)):
        return build_radical_factor_plan(context, vertical_roots=True)

    def calculation(formula: str, match: re.Match[str]) -> tuple[tuple[str, ...], Fraction]:
        coefficients: list[int] = []
        decomposed: list[str] = []
        expanded: list[str] = []
        all_factors: Counter[int] = Counter()
        radicand_product = 1
        for term in formula.split(r"\cdot"):
            parsed = re.fullmatch(r"(\d*)\\sqrt\{(\d+)\}", term)
            coefficient, radicand = int(parsed[1] or 1), int(parsed[2])
            coefficients.append(coefficient)
            factors = _prime_factors(radicand)
            all_factors.update(factors)
            radicand_product *= radicand
            factor_text = r"\cdot".join(str(p) for p, count in factors.items() for _ in range(count)) or "1"
            prefix = str(coefficient) if coefficient != 1 else ""
            decomposed.append(prefix + rf"\sqrt{{{factor_text}}}")
            if coefficient != 1:
                expanded.append(str(coefficient))
            expanded.extend(rf"\sqrt{{{p}}}" for p, count in factors.items() for _ in range(count))
        if any(count % 2 for count in all_factors.values()):
            raise RightTrianglePlanError("root product is not a rational number")
        outside = [str(c) for c in coefficients if c != 1]
        pairs = [rf"(\sqrt{{{p}}})^{{2}}" for p, count in sorted(all_factors.items()) for _ in range(count // 2)]
        integers = [str(p) for p, count in sorted(all_factors.items()) for _ in range(count // 2)]
        root = isqrt(radicand_product)
        result = root
        for coefficient in coefficients:
            result *= coefficient
        candidates = (
            formula,
            r"\cdot".join(decomposed),
            r"\cdot".join(expanded) or "1",
            r"\cdot".join(outside + pairs) or "1",
            r"\cdot".join(outside + integers) or "1",
        )
        steps: list[str] = []
        for step in candidates:
            if not steps or step != steps[-1]:
                steps.append(step)
        if steps[-1] == str(result):
            steps.pop()
        return tuple(steps), Fraction(result)

    return _plan(context, formula_pattern=_ROOT_PRODUCT, calculation=calculation, vertical_roots=True)


_POWER_PRODUCT = re.compile(
    r"(?P<base>[1-9]\d{0,2})\^\{(?P<m>-?\d{1,2})\}\\cdot"
    r"\((?P=base)\^\{(?P<n>-?\d{1,2})\}\)\^\{(?P<p>-?\d{1,2})\}"
)


def build_power_product_plan(context: dict[str, Any], *, parent_solution_html: str = "") -> RepairPlan:
    """Use the parent's power-of-a-power and common-base product identities."""
    content = _normalized_content(context)
    condition = _section(content, "condition")
    solution = _section(content, "solution")
    answer_section = _section(content, "answer")
    if condition is None or content.get("assets") or condition.get("asset_keys"):
        raise RightTrianglePlanError("power products must be text-only")
    soup = BeautifulSoup(str(condition.get("html") or ""), "html.parser")
    intro = soup.find("p")
    formulas = intro.select("span[data-inline-latex]") if intro else []
    if len(formulas) != 1:
        raise RightTrianglePlanError("power-product introductory paragraph must contain one formula")
    formula = str(formulas[0]['data-inline-latex']).replace(' ', '').replace(r'\left', '').replace(r'\right', '')
    match = _POWER_PRODUCT.fullmatch(formula)
    if match is None:
        raise RightTrianglePlanError("condition does not match the common-base power product")
    formulas[0].replace_with('FORMULA')
    prose = ' '.join(intro.get_text(' ', strip=True).replace('\u00ad', '').split())
    prose = re.sub(r'\s+([.?])', r'\1', prose)
    multiple_choice = prose == 'Какое из данных ниже чисел является значением выражения FORMULA?'
    if not multiple_choice and prose not in {'Найдите значение выражения FORMULA.', 'Найдите значение выражения FORMULA'}:
        raise RightTrianglePlanError("unsupported power-product question")
    base, m, n, p = (int(match[name]) for name in ('base', 'm', 'n', 'p'))
    nested, exponent = n * p, m + n * p
    if abs(nested) > 100 or abs(exponent) > 100:
        raise RightTrianglePlanError("power-product exponent exceeds the supported range")
    value = Fraction(base) ** exponent
    if multiple_choice:
        cells = soup.select('table td')
        if len(cells) != 4 or len(soup.select('table')) != 1:
            raise RightTrianglePlanError("expected exactly four power-product options")
        matches: list[int] = []
        for index, cell in enumerate(cells, 1):
            options = cell.select('span[data-inline-latex]')
            if len(options) != 1 or cell.get_text('', strip=True) != f'{index})':
                raise RightTrianglePlanError("ambiguous power-product option markup")
            try:
                option_value = parse_rational(str(options[0]['data-inline-latex']))
            except ValueError as exc:
                raise RightTrianglePlanError("unsupported power-product option value") from exc
            if option_value == value:
                matches.append(index)
        if len(matches) != 1:
            raise RightTrianglePlanError("power product must match exactly one option")
        answer = str(matches[0])
        soup.find('table').decompose()
    else:
        answer = _decimal(value)
    # Reject extra conditions outside the recognized question/options.
    intro.decompose()
    if soup.get_text('', strip=True) or soup.select('span[data-inline-latex]'):
        raise RightTrianglePlanError("unexpected content outside the power-product question")
    addition = f'{m}+({nested})' if nested < 0 else f'{m}+{nested}'
    lines = [formula, rf'{base}^{{{m}}}\cdot{base}^{{{nested}}}',
             rf'{base}^{{{addition}}}', rf'{base}^{{{exponent}}}']
    lines.append(_fraction(value))
    html = ('<p>Используя формулы <span data-inline-latex="(a^{b})^{c}=a^{bc}"></span> '
            'и <span data-inline-latex="a^{b}\\cdot a^{c}=a^{b+c}"></span>, получаем:</p>')
    chain = '='.join(lines)
    html += f'<center><p><span data-inline-latex="{chain}"></span>.</p></center>'
    if multiple_choice:
        html += f'<p>Получили <span data-inline-latex="{_fraction(value)}"></span> — вариант {answer}.</p>'
    changes: list[dict[str, Any]] = []
    current_solution = str((solution or {}).get('html') or '')
    preserve_parent = bool(parent_solution_html) and current_solution == parent_solution_html
    if not preserve_parent and current_solution != html:
        changes.append(_section_transformation(solution, 'solution', 'Решение', html))
    current_answer = BeautifulSoup(str((answer_section or {}).get('html') or ''), 'html.parser').get_text('', strip=True)
    if current_answer != answer:
        changes.append(_section_transformation(answer_section, 'answer', 'Ответ',
                       f'<p><span data-effect="spaced">{answer}</span></p>'))
    return RepairPlan(answer=answer, transformations=tuple(changes))
