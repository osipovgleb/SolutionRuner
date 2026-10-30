"""Equal-fractions planner for group 101879."""

from __future__ import annotations

import re
from fractions import Fraction
from typing import Any

from bs4 import BeautifulSoup

from ..core.numbers import format_answer, format_latex_fraction
from ..triangles.isosceles.planner import (
    _normalized_content,
    _section,
    _section_transformation,
)
from ..triangles.right.planner import RepairPlan, RightTrianglePlanError
from .equation_conditions import read_equation_prompt
from .solution_formatting import vertical_derivation

RULE = "elementary-equations-101879-equal-numerators"
_D = r"\d+(?:\{,\}\d+)?"
_F = re.compile(
    rf"\\frac\{{x(?P<ns>[+-])(?P<n>{_D})\}}\{{(?P<a>-?(?:{_D})?)x(?P<as>[+-])(?P<b>{_D})\}}=\\frac\{{x(?P<ns2>[+-])(?P<n2>{_D})\}}\{{(?P<c>-?(?:{_D})?)x(?:(?P<cs>[+-])(?P<d>{_D}))?\}}"
)
_K = re.compile(
    r"в ответ(?:е)? запишите (?P<k>больший|меньший)(?: из)? (?:корень|корней)\.?$"
)


def _number(value):
    return format_answer(value, allow_latex_fraction=True).replace(",", "{,}")


def _linear(coefficient, constant):
    prefix = (
        "" if coefficient == 1 else "-" if coefficient == -1 else _number(coefficient)
    )
    variable = prefix + "x"
    return (
        variable
        if not constant
        else variable + ("+" if constant > 0 else "-") + _number(abs(constant))
    )


def _polynomial(A, B, C):
    def term(v, suffix, first=False):
        if not v:
            return ""
        sign = "-" if v < 0 else ("" if first else "+")
        mag = abs(v)
        coef = "" if suffix and mag == 1 else _number(mag)
        return sign + coef + suffix

    return term(A, "x^{2}", True) + term(B, "x") + term(C, "")


def build_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str | None,
    parent_solution_html: str = "",
    current_asset_content_type: str | None = None,
) -> RepairPlan:
    del parent_solution_html, current_asset_content_type
    if parent_condition_asset_id not in (None, ""):
        raise RightTrianglePlanError("group 101879 must not have assets")
    c = _normalized_content(context)
    q = _section(c, "condition")
    ans = _section(c, "answer")
    sol = _section(c, "solution")
    if q is None or c.get("assets") or tuple(q.get("asset_keys") or ()):
        raise RightTrianglePlanError("condition incomplete")
    soup = BeautifulSoup(str(q.get("html") or ""), "html.parser")
    read_equation_prompt(
        str(q.get("html") or ""), allow_selector=True, error_type=RightTrianglePlanError
    )
    sp = soup.find_all("span")
    if len(sp) != 1 or sp[0].get_text(strip=True):
        raise RightTrianglePlanError("condition ambiguous")
    f = str(sp[0].get("data-inline-latex") or "")
    m = _F.fullmatch(f)
    text = " ".join(soup.get_text(" ", strip=True).replace("\u00ad", "").split())
    k = _K.search(text)
    if not m or not k or m["ns"] != m["ns2"] or m["n"] != m["n2"]:
        raise RightTrianglePlanError("condition does not match group 101879")
    val = lambda s: Fraction(str(s).replace("{,}", "."))
    n = val(m["n"]) if m["ns"] == "+" else -val(m["n"])
    a = val(m["a"] or "1")
    b = val(m["b"]) if m["as"] == "+" else -val(m["b"])
    cc = val(m["c"] or "1")
    d = (
        Fraction(0)
        if m["cs"] is None
        else (val(m["d"]) if m["cs"] == "+" else -val(m["d"]))
    )
    if a == cc:
        raise RightTrianglePlanError("equal denominators")
    roots = sorted((Fraction(-n), Fraction(d - b, a - cc)))
    roots = tuple(x for x in roots if a * x + b and cc * x + d)
    if not roots:
        raise RightTrianglePlanError("no roots satisfy domain")
    chosen = roots[-1] if k["k"] == "больший" else roots[0]

    values = "\\\\".join("x=" + _number(x) for x in roots)
    left_den = _linear(a, b)
    right_den = _linear(cc, d)
    primary = (
        '<p>Дроби с оди­на­ко­вы­ми чис­ли­те­ля­ми равны в двух слу­ча­ях:</p><ol type="a"><li>зна­ме­на­те­ли этих дро­бей равны и при этом от­лич­ны от нуля;</li><li>чис­ли­те­ли дро­бей равны нулю, при этом все зна­ме­на­те­ли от­лич­ны от нуля.</li></ol><p>По­лу­ча­ем:</p>'
        + f'<center><p><span data-inline-latex="{f}\\iff \\begin{{cases}}{left_den}\\ne0\\\\{right_den}\\ne0\\\\\\left[\\begin{{aligned}}x{m["ns"]}{abs(n)}=0\\\\{left_den}={right_den}\\end{{aligned}}\\right.\\end{{cases}}\\iff \\left[\\begin{{aligned}}{values}\\end{{aligned}}\\right."></span>.</p></center>'
        + f"<p>{'Боль­ший' if k['k'] == 'больший' else 'Мень­ший'} из най­ден­ных кор­ней равен {_number(chosen)}.</p>"
    )

    ntext = _linear(Fraction(1), n)
    left = _polynomial(cc, cc * n + d, d * n)
    right = _polynomial(a, a * n + b, b * n)
    quadratic = _polynomial(cc - a, cc * n + d - a * n - b, d * n - b * n)
    first = f"\\begin{{cases}}{left_den}\\ne0\\\\{right_den}\\ne0\\\\({ntext})({right_den})=({ntext})({left_den})\\end{{cases}}"
    fraction_exclusions = f"x\\ne{format_latex_fraction(Fraction(-b, a))}\\\\x\\ne{format_latex_fraction(Fraction(-d, cc))}"
    decimal_exclusions = (
        f"x\\ne{_number(Fraction(-b, a))}\\\\x\\ne{_number(Fraction(-d, cc))}"
    )
    second = f"\\begin{{cases}}{fraction_exclusions}\\\\{left}={right}\\end{{cases}}"
    third = f"\\begin{{cases}}{decimal_exclusions}\\\\{quadratic}=0\\end{{cases}}"
    fourth = f"\\begin{{cases}}{decimal_exclusions}\\\\\\left[\\begin{{aligned}}{values}\\end{{aligned}}\\right.\\end{{cases}}"
    alternative = (
        "<p><b>Приведём другое решение</b></p><p>Используем свойство пропорции, раскроем скобки, получим квадратное уравнение:</p>"
        + f'<center><p><span data-inline-latex="{f}\\iff {first}\\iff {second}\\iff {third}\\iff {fourth}"></span>.</p></center>'
        + f"<p>{'Боль­ший' if k['k'] == 'больший' else 'Мень­ший'} из най­денных кор­ней равен {_number(chosen)}.</p>"
    )
    h = vertical_derivation(primary + alternative)
    out = _number(chosen)
    ch = []
    if sol is None or sol.get("html") != h:
        ch.append(_section_transformation(sol, "solution", "Решение", h))
    cur = (
        BeautifulSoup(str(ans.get("html") or "") if ans else "", "html.parser")
        .get_text("", strip=True)
        .replace(" ", "")
    )
    if cur != out:
        ch.append(
            _section_transformation(
                ans,
                "answer",
                "Ответ",
                f'<p><span data-effect="spaced">{out}</span></p>',
            )
        )
    return RepairPlan(answer=out, transformations=tuple(ch))
