"""Fail-closed planner for tabular trigonometric equations with affine arguments."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from html import escape
import json
from pathlib import Path
import re
from typing import Any

from bs4 import BeautifulSoup

from solution_runner.pipelines.core.numbers import format_answer, format_latex_fraction
from solution_runner.pipelines.equations.group_26650 import _parse_linear
from solution_runner.pipelines.equations.group_26656 import RepairPlan

RULE = "trigonometric-table-value-affine-argument"
_ASSETS = json.loads((Path(__file__).parent / "assets/trigonometry/source-assets.json").read_text())


class UnsupportedCondition(ValueError):
    """Raised before mutation for a form that has not been reviewed."""


@dataclass(frozen=True)
class _Value:
    angles: tuple[Fraction, ...]  # coefficients of pi
    period: int
    asset: str


def _v(angles: tuple[Fraction, ...], period: int, asset: str) -> _Value:
    return _Value(angles, period, asset)


_VALUES: dict[str, dict[str, _Value]] = {
    "cos": {
        "1": _v((Fraction(0),), 2, "cos-one.svg"), "-1": _v((Fraction(1),), 2, "cos-minus-one.svg"), "0": _v((Fraction(1, 2),), 2, "cos-zero.svg"),
        r"\frac{1}{2}": _v((Fraction(1, 3), Fraction(-1, 3)), 2, "cos-half.svg"), r"-\frac{1}{2}": _v((Fraction(2, 3), Fraction(-2, 3)), 2, "cos-minus-half.svg"),
        r"\frac{\sqrt{2}}{2}": _v((Fraction(1, 4), Fraction(-1, 4)), 2, "cos-sqrt2-over-2.svg"), r"-\frac{\sqrt{2}}{2}": _v((Fraction(3, 4), Fraction(-3, 4)), 2, "cos-minus-sqrt2-over-2.svg"),
        r"\frac{\sqrt{3}}{2}": _v((Fraction(1, 6), Fraction(-1, 6)), 2, "cos-sqrt3-over-2.svg"), r"-\frac{\sqrt{3}}{2}": _v((Fraction(5, 6), Fraction(-5, 6)), 2, "cos-minus-sqrt3-over-2.svg"),
    },
    "sin": {
        "0": _v((Fraction(0),), 2, "sin-zero.svg"), "1": _v((Fraction(1, 2),), 2, "sin-one.svg"), "-1": _v((Fraction(-1, 2),), 2, "sin-minus-one.svg"),
        r"\frac{1}{2}": _v((Fraction(1, 6), Fraction(5, 6)), 2, "sin-half.svg"), r"-\frac{1}{2}": _v((Fraction(-1, 6), Fraction(7, 6)), 2, "sin-minus-half.svg"),
        r"\frac{\sqrt{2}}{2}": _v((Fraction(1, 4), Fraction(3, 4)), 2, "sin-sqrt2-over-2.svg"), r"-\frac{\sqrt{2}}{2}": _v((Fraction(-1, 4), Fraction(5, 4)), 2, "sin-minus-sqrt2-over-2.svg"),
        r"\frac{\sqrt{3}}{2}": _v((Fraction(1, 3), Fraction(2, 3)), 2, "sin-sqrt3-over-2.svg"), r"-\frac{\sqrt{3}}{2}": _v((Fraction(-1, 3), Fraction(4, 3)), 2, "sin-minus-sqrt3-over-2.svg"),
    },
    "tg": {
        "0": _v((Fraction(0),), 1, "tg-zero.svg"), "1": _v((Fraction(1, 4),), 1, "tg-one.svg"), "-1": _v((Fraction(-1, 4),), 1, "tg-minus-one.svg"),
        r"\sqrt{3}": _v((Fraction(1, 3),), 1, "tg-sqrt3.svg"), r"-\sqrt{3}": _v((Fraction(-1, 3),), 1, "tg-minus-sqrt3.svg"),
        r"\frac{1}{\sqrt{3}}": _v((Fraction(1, 6),), 1, "tg-one-over-sqrt3.svg"), r"-\frac{1}{\sqrt{3}}": _v((Fraction(-1, 6),), 1, "tg-minus-one-over-sqrt3.svg"),
    },
}
_FORMULA = re.compile(r"\\(?P<function>sin|cos|tg)\\frac\{\\pi(?P<argument>\([^{}]+\)|[^{}]+)\}\{(?P<denominator>[1-9]\d*)\}=(?P<value>.+)")


def _latex(value: Fraction) -> str:
    return format_latex_fraction(value)


def _table_number(value: Fraction) -> str:
    """Prefer the decimal-comma form in substitutions and the selected root."""
    return format_answer(value, allow_latex_fraction=True).replace(",", "{,}")


def _pi_fraction(value: Fraction) -> str:
    """Render a multiple of π with π inside the numerator."""
    if value == 0:
        return "0"
    sign = "-" if value < 0 else ""
    numerator = abs(value.numerator)
    if value.denominator == 1:
        return f"{sign}{'' if numerator == 1 else numerator}\\pi"
    top = r"\pi" if numerator == 1 else rf"{numerator}\pi"
    return rf"{sign}\frac{{{top}}}{{{value.denominator}}}"


def _union(lines: list[str]) -> str:
    """Render one equation or a visible совокупность with one parameter k."""
    if len(lines) == 1:
        return lines[0] + r",\quad k\in\mathbb Z"
    return r"\left[\begin{aligned}" + r"\\".join(lines) + r"\end{aligned}\right.,\quad k\in\mathbb Z"


def _ceil(value: Fraction) -> int:
    return -((-value.numerator) // value.denominator)


def _section(content: dict[str, Any], key: str) -> dict[str, Any] | None:
    matches = [item for item in content.get("sections", []) if isinstance(item, dict) and item.get("key") == key]
    if len(matches) > 1:
        raise UnsupportedCondition(f"multiple {key} sections")
    return matches[0] if matches else None


def _rewrite(section: dict[str, Any] | None, key: str, title: str, html: str, asset_keys: list[str] = []) -> dict[str, Any]:
    target = str((section or {}).get("transformation_target_id") or f"section:{key}:1")
    return {"transformation_target_id": target, "operation": "rewrite" if section else "add", "value": {"title": title, "html": html, "asset_keys": asset_keys}}


def _parse(formula: str) -> tuple[str, str, int, int, int, _Value]:
    match = _FORMULA.fullmatch(formula)
    if not match:
        raise UnsupportedCondition("unsupported trigonometric equation")
    function, argument, denominator, value = match.group("function", "argument", "denominator", "value")
    argument = (argument[1:-1] if argument.startswith("(") else argument).replace(" ", "")
    try:
        constant, coefficient = _parse_linear(argument)
    except ValueError as error:
        raise UnsupportedCondition("argument is not affine") from error
    if coefficient == 0:
        raise UnsupportedCondition("argument has no x")
    value = value.replace("0{,}5", r"\frac{1}{2}").replace("-0{,}5", r"-\frac{1}{2}")
    spec = _VALUES.get(function, {}).get(value)
    if spec is None:
        raise UnsupportedCondition("value is not in reviewed table")
    return function, argument, int(denominator), constant, coefficient, spec


def _pick(a: Fraction, b: Fraction, largest_negative: bool) -> tuple[int, Fraction]:
    """Select the extremal root of a+b*k with k integer."""
    boundary = -a / b
    if largest_negative:
        k = _ceil(boundary) - 1 if b > 0 else boundary.numerator // boundary.denominator + 1
    else:
        k = boundary.numerator // boundary.denominator + 1 if b > 0 else _ceil(boundary) - 1
    answer = a + b * k
    if (largest_negative and answer >= 0) or (not largest_negative and answer <= 0):
        raise UnsupportedCondition("root selection is ambiguous")
    return k, answer


def _required(value: Fraction, *, largest_negative: bool) -> bool:
    """Return whether a root has the sign requested by the condition."""
    return value < 0 if largest_negative else value > 0


def _selection_rows(
    a: Fraction,
    b: Fraction,
    *,
    largest_negative: bool,
) -> tuple[list[tuple[int, Fraction]], tuple[int, Fraction]]:
    """Trace consecutive k values from zero until the series crosses zero."""
    if b == 0:
        raise UnsupportedCondition("root series is constant")
    current = a
    if current > 0:
        direction = -1 if b > 0 else 1
    elif current < 0:
        direction = 1 if b > 0 else -1
    else:
        direction = (-1 if b > 0 else 1) if largest_negative else (1 if b > 0 else -1)

    rows = [(0, current)]
    selected = (0, current) if _required(current, largest_negative=largest_negative) else None
    k = 0
    while len(rows) < 100:
        k += direction
        value = a + b * k
        rows.append((k, value))
        if _required(value, largest_negative=largest_negative):
            selected = (k, value)
            if not _required(current, largest_negative=largest_negative):
                return rows, selected
        elif selected is not None:
            return rows, selected
        current = value
    raise UnsupportedCondition("root selection did not cross zero")


def _substitution(name: str, a: Fraction, b: Fraction, k: int, value: Fraction) -> str:
    """Render one visible substitution into a root series."""
    coefficient = _latex(b)
    middle = f"+{coefficient}" if b >= 0 else coefficient
    return rf"{name}={_latex(a)}{middle}\cdot({k})={_table_number(value)}"


def _pi_times(argument: str) -> str:
    """Use parentheses only when the argument is not the lone variable ``x``."""
    return rf"\pi {argument}" if argument == "x" else rf"\pi({argument})"


def _root_table(
    branches: list[tuple[Fraction, Fraction]],
    *,
    largest_negative: bool,
) -> tuple[str, list[tuple[int, Fraction]]]:
    """Render one k-by-k table for every root series and return nearest roots."""
    traces = [_selection_rows(a, b, largest_negative=largest_negative) for a, b in branches]
    rows_by_branch = [trace[0] for trace in traces]
    selected = [trace[1] for trace in traces]
    variable_names = ["x"] * len(branches)
    header_attributes = ' data-align="center" data-cell-tone="source-header" data-valign="middle"'
    labels = "<tr>" + "".join(
        f"<th colspan=\"2\"{header_attributes}>{'Корни' if len(branches) == 1 else ('Первый' if index == 1 else 'Второй') + ' корень'}</th>"
        for index in range(1, len(branches) + 1)
    ) + "</tr>"
    body: list[str] = []
    row_count = max(len(rows) for rows in rows_by_branch)
    for row_index in range(row_count):
        cells: list[str] = []
        for name, (a, b), rows in zip(variable_names, branches, rows_by_branch, strict=True):
            if row_index < len(rows):
                k, value = rows[row_index]
                substitution = _substitution(name, a, b, k, value)
                cells.extend((
                    rf'<td nowrap><span data-inline-latex="k={k}"></span></td>',
                    rf'<td nowrap><span data-inline-latex="{substitution}"></span></td>',
                ))
            else:
                cells.extend(("<td></td>", "<td></td>"))
        body.append("<tr>" + "".join(cells) + "</tr>")
    return "<table><thead>" + labels + "</thead><tbody>" + "".join(body) + "</tbody></table>", selected


def build_repair_plan(formula: str, *, largest_negative: bool) -> RepairPlan:
    function, argument, denominator, constant, coefficient, spec = _parse(formula)
    source_match = _FORMULA.fullmatch(formula)
    if source_match is None:  # Kept for a clear invariant beside _parse.
        raise UnsupportedCondition("unsupported trigonometric equation")
    condition_formula = (
        rf"\{function} \frac{{{_pi_times(argument)}}}{{{denominator}}}="
        + str(source_match.group("value") or "").replace(" ", "")
    )
    branches: list[tuple[Fraction, Fraction]] = []
    for angle in spec.angles:
        branches.append((Fraction(denominator) * angle - constant, Fraction(denominator * spec.period, coefficient)))
    sign = "отрицательный" if largest_negative else "положительный"
    algorithm = (
        '<ol>'
        '<li>Подставляем <span data-inline-latex="k=0"></span> в каждое из уравнений</li>'
        '<li>Изменяем <span data-inline-latex="k"></span> на единицу «вверх» или «вниз», пока корень не перейдёт через ноль</li>'
        f'<li>Выбираем ближайший к нулю {sign} корень</li>'
        '</ol>'
    )
    normalized_branches = [(shift / coefficient, step) for shift, step in branches]
    table, roots = _root_table(
        normalized_branches,
        largest_negative=largest_negative,
    )
    answer_value = (max if largest_negative else min)(root for _, root in roots)
    answer = format_answer(answer_value, allow_latex_fraction=True)
    names = tuple("k" for _ in branches)
    initial_equations = [
        rf"\frac{{{_pi_times(argument)}}}{{{denominator}}}={_pi_fraction(angle)}+{_pi_fraction(Fraction(spec.period))} {name}"
        for angle, name in zip(spec.angles, names, strict=True)
    ]
    argument_equations = [
        rf"{argument}={_latex(Fraction(denominator) * angle)}+{denominator * spec.period}{name}"
        for angle, name in zip(spec.angles, names, strict=True)
    ]
    x_equations = [
        rf"x={_latex(shift / coefficient)}+{_latex(step)}{name}"
        for (shift, step), name in zip(branches, names, strict=True)
    ]
    equations = (
        '<center><p><span data-formula-render-mode="display" data-inline-latex="'
        + r"\iff ".join((condition_formula, _union(initial_equations), _union(argument_equations), _union(x_equations)))
        + '"></span></p></center>'
    )
    selected_index = next(index for index, (_, root) in enumerate(roots) if root == answer_value)
    selected_root = rf"x={_table_number(roots[selected_index][1])}"
    # This generic plan is rendered with the matching reusable SourceAsset ID.
    # ``build_context_repair_plan`` swaps it for the problem-local ordinary
    # asset, because Normalized content may only reference ordinary assets.
    asset_id = _ASSETS[spec.asset]
    asset_html = f'<center><p><img alt="Табличное значение {function}" data-asset-id="{asset_id}" data-asset-key="image_1" src="/assets/{asset_id}"/></p></center>'
    kind = "наибольший отрицательный" if largest_negative else "наименьший положительный"
    solution = (f"<p>По таблице значений тригонометрических функций:</p>{asset_html}"
                f'<p>Получаем:</p>{equations}'
                f'<p>Общий алгоритм:</p>{algorithm}{table}'
                f'<p>Ближайший к нулю {sign} корень: <span data-inline-latex="{selected_root}"></span></p>')
    return RepairPlan(answer=answer, condition_html="", solution_html=solution)


def _condition_formula_and_selection(context: dict[str, Any]) -> tuple[dict[str, Any], str, bool]:
    """Read the supported source formula and requested extremal root once."""
    content = context.get("normalized_content")
    if not isinstance(content, dict) or content.get("format") != "teacherhelper-normalized" or content.get("schema_version") != 3:
        raise UnsupportedCondition("schema-v3 normalized content is required")
    condition, answer, solution = (_section(content, key) for key in ("condition", "answer", "solution"))
    if condition is None:
        raise UnsupportedCondition("condition is required")
    soup = BeautifulSoup(str(condition.get("html") or ""), "html.parser")
    spans = soup.find_all("span", attrs={"data-inline-latex": True})
    if len(spans) != 1:
        raise UnsupportedCondition("condition must have one formula")
    formula = str(spans[0].get("data-inline-latex") or "")
    formula = re.sub(r"\\(sin|cos|tg)\s+(?=\\frac)", r"\\\1", formula)
    formula = re.sub(r"\s*=\s*", "=", formula)
    text = soup.get_text(" ", strip=True).replace("\u00ad", "")
    largest_negative = "наибольш" in text and "отрицатель" in text
    smallest_positive = "наименьш" in text and "положитель" in text
    if largest_negative == smallest_positive:
        raise UnsupportedCondition("root selection wording is unsupported")
    return condition, formula, largest_negative


def required_assets(context: dict[str, Any]) -> tuple[dict[str, str], ...]:
    """Select the one reviewed diagram demanded by the condition's table value."""
    _, formula, _ = _condition_formula_and_selection(context)
    function, _, _, _, _, spec = _parse(formula)
    return ({
        "source_asset_id": str(_ASSETS[spec.asset]),
        "section_id": "solution:1",
        "alt_text": f"Табличное значение {function}",
    },)


def build_context_repair_plan(context: dict[str, Any]) -> RepairPlan:
    content = context.get("normalized_content")
    if not isinstance(content, dict):
        raise UnsupportedCondition("schema-v3 normalized content is required")
    condition, formula, largest_negative = _condition_formula_and_selection(context)
    answer, solution = (_section(content, key) for key in ("answer", "solution"))
    planned = build_repair_plan(formula, largest_negative=largest_negative)
    _, _, _, _, _, spec = _parse(formula)
    source_asset_id = _ASSETS[spec.asset]
    attached_assets = [
        item for item in content.get("assets", [])
        if isinstance(item, dict) and item.get("asset_key") and item.get("asset_id")
    ]
    # The runtime attaches the required shared SVG before planning.  Refuse any
    # unrelated legacy picture instead of silently using a wrong diagram.
    matching_assets = [item for item in attached_assets if item.get("asset_id") == source_asset_id]
    if len(matching_assets) != 1:
        raise UnsupportedCondition("the required trigonometry asset is not attached")
    asset_id = str(matching_assets[0]["asset_id"])
    asset_key = str(matching_assets[0]["asset_key"])
    # SourceAssets are a reusable library.  A solution, however, must point at
    # the ordinary asset already attached to this exact problem.  Do not write
    # a SourceAsset ID into Normalized content.
    planned = RepairPlan(
        answer=planned.answer,
        condition_html=planned.condition_html,
        solution_html=(
            planned.solution_html
            .replace(source_asset_id, asset_id)
            .replace('data-asset-key="image_1"', f'data-asset-key="{asset_key}"')
        ),
    )
    transformations: list[dict[str, Any]] = []
    if solution is None or str(solution.get("html") or "") != planned.solution_html:
        transformations.append(_rewrite(solution, "solution", "Решение", planned.solution_html, [asset_key]))
    current = BeautifulSoup(str((answer or {}).get("html") or ""), "html.parser").get_text("", strip=True).replace(" ", "")
    if current != planned.answer:
        transformations.append(_rewrite(answer, "answer", "Ответ", f'<p><span data-effect="spaced">{planned.answer}</span></p>'))
    return RepairPlan(answer=planned.answer, condition_html=str(condition.get("html") or ""), solution_html=planned.solution_html, transformations=tuple(transformations))
