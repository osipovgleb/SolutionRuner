"""Plan products of powers with a shared base."""

from __future__ import annotations

import re
from fractions import Fraction
from typing import Any

from bs4 import BeautifulSoup

from solution_runner.pipelines.core.numbers import parse_rational

from ..triangles.isosceles.planner import _normalized_content as _choice_content
from ..triangles.isosceles.planner import _section, _section_transformation
from ..triangles.right.planner import RepairPlan, RightTrianglePlanError
from .numeric_format import _decimal, _fraction

_POWER_PRODUCT = re.compile(
    r"(?P<base>[1-9]\d{0,2})\^\{(?P<m>-?\d{1,2})\}\\cdot"
    r"\((?P=base)\^\{(?P<n>-?\d{1,2})\}\)\^\{(?P<p>-?\d{1,2})\}"
)


def _parse_question(condition):
    soup = BeautifulSoup(str(condition.get("html") or ""), "html.parser")
    intro = soup.find("p")
    formulas = intro.select("span[data-inline-latex]") if intro else []
    if len(formulas) != 1:
        raise RightTrianglePlanError(
            "power-product introductory paragraph must contain one formula"
        )
    formula = (
        str(formulas[0]["data-inline-latex"])
        .replace(" ", "")
        .replace(r"\left", "")
        .replace(r"\right", "")
    )
    match = _POWER_PRODUCT.fullmatch(formula)
    if match is None:
        raise RightTrianglePlanError(
            "condition does not match the common-base power product"
        )
    formulas[0].replace_with("FORMULA")
    prose = " ".join(intro.get_text(" ", strip=True).replace("\u00ad", "").split())
    prose = re.sub(r"\s+([.?])", r"\1", prose)
    multiple_choice = (
        prose == "Какое из данных ниже чисел является значением выражения FORMULA?"
    )
    if not multiple_choice and prose not in {
        "Найдите значение выражения FORMULA.",
        "Найдите значение выражения FORMULA",
    }:
        raise RightTrianglePlanError("unsupported power-product question")
    return soup, intro, formula, match, multiple_choice


def _choice_answer(soup, value):
    cells = soup.select("table td")
    if len(cells) != 4 or len(soup.select("table")) != 1:
        raise RightTrianglePlanError("expected exactly four power-product options")
    matches: list[int] = []
    for index, cell in enumerate(cells, 1):
        options = cell.select("span[data-inline-latex]")
        if len(options) != 1 or cell.get_text("", strip=True) != f"{index})":
            raise RightTrianglePlanError("ambiguous power-product option markup")
        try:
            option_value = parse_rational(str(options[0]["data-inline-latex"]))
        except ValueError as exc:
            raise RightTrianglePlanError(
                "unsupported power-product option value"
            ) from exc
        if option_value == value:
            matches.append(index)
    if len(matches) != 1:
        raise RightTrianglePlanError("power product must match exactly one option")
    return str(matches[0])


def build_power_product_plan(
    context: dict[str, Any], *, parent_solution_html: str = ""
) -> RepairPlan:
    """Use the parent's power-of-a-power and common-base product identities."""
    content = _choice_content(context)
    condition = _section(content, "condition")
    solution = _section(content, "solution")
    answer_section = _section(content, "answer")
    if condition is None or content.get("assets") or condition.get("asset_keys"):
        raise RightTrianglePlanError("power products must be text-only")
    soup, intro, formula, match, multiple_choice = _parse_question(condition)
    base, m, n, p = (int(match[name]) for name in ("base", "m", "n", "p"))
    nested, exponent = n * p, m + n * p
    if abs(nested) > 100 or abs(exponent) > 100:
        raise RightTrianglePlanError(
            "power-product exponent exceeds the supported range"
        )
    value = Fraction(base) ** exponent
    if multiple_choice:
        answer = _choice_answer(soup, value)
        soup.find("table").decompose()
    else:
        answer = _decimal(value)
    # Reject extra conditions outside the recognized question/options.
    intro.decompose()
    if soup.get_text("", strip=True) or soup.select("span[data-inline-latex]"):
        raise RightTrianglePlanError(
            "unexpected content outside the power-product question"
        )
    addition = f"{m}+({nested})" if nested < 0 else f"{m}+{nested}"
    lines = [
        formula,
        rf"{base}^{{{m}}}\cdot{base}^{{{nested}}}",
        rf"{base}^{{{addition}}}",
        rf"{base}^{{{exponent}}}",
    ]
    lines.append(_fraction(value))
    html = (
        '<p>Используя формулы <span data-inline-latex="(a^{b})^{c}=a^{bc}"></span> '
        'и <span data-inline-latex="a^{b}\\cdot a^{c}=a^{b+c}"></span>, получаем:</p>'
    )
    chain = "=".join(lines)
    html += f'<center><p><span data-inline-latex="{chain}"></span>.</p></center>'
    if multiple_choice:
        html += f'<p>Получили <span data-inline-latex="{_fraction(value)}"></span> — вариант {answer}.</p>'
    changes: list[dict[str, Any]] = []
    current_solution = str((solution or {}).get("html") or "")
    preserve_parent = (
        bool(parent_solution_html) and current_solution == parent_solution_html
    )
    if not preserve_parent and current_solution != html:
        changes.append(_section_transformation(solution, "solution", "Решение", html))
    current_answer = BeautifulSoup(
        str((answer_section or {}).get("html") or ""), "html.parser"
    ).get_text("", strip=True)
    if current_answer != answer:
        changes.append(
            _section_transformation(
                answer_section,
                "answer",
                "Ответ",
                f'<p><span data-effect="spaced">{answer}</span></p>',
            )
        )
    return RepairPlan(answer=answer, transformations=tuple(changes))
