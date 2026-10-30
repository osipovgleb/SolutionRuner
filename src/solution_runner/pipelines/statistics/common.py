"""Validated mathematical markup and exact statistical presentation."""

import re
from dataclasses import replace
from fractions import Fraction
from html import escape
from math import isqrt

from bs4 import BeautifulSoup

from solution_runner.pipelines.core.numbers import (
    format_answer,
    format_latex_fraction,
    parse_rational,
)
from solution_runner.pipelines.probability.common import (
    COUNT,
    NUMBER,
    UnsupportedCondition,
    count,
    finish,
    line,
    normalize,
    require_content,
)
from solution_runner.pipelines.word_problems.common import rewrite, section

SIGNED = rf"-?{NUMBER}"
_CASE_WORDS = {
    "двух": 2,
    "трех": 3,
    "четырех": 4,
    "пяти": 5,
    "шести": 6,
    "семи": 7,
    "восьми": 8,
    "девяти": 9,
    "десяти": 10,
}
CASED_COUNT = "(?:" + COUNT + "|" + "|".join(_CASE_WORDS) + ")"


def integer(token):
    token = normalize(token)
    return _CASE_WORDS[token] if token in _CASE_WORDS else count(token)


def number(token):
    return parse_rational(token.replace("−", "-"))


def fmt(value):
    return format_latex_fraction(Fraction(value))


def sqrt_exact(value):
    if value < 0:
        raise UnsupportedCondition("a variance or square root cannot be negative")
    a, b = isqrt(value.numerator), isqrt(value.denominator)
    if a * a != value.numerator or b * b != value.denominator:
        raise UnsupportedCondition("the requested exact answer is irrational")
    return Fraction(a, b)


def probability(value, *, positive=False):
    if not (0 < value <= 1 if positive else 0 <= value <= 1):
        raise UnsupportedCondition("the event probability is outside its valid range")
    return value


def _visible(soup):
    for tag in soup.find_all("var"):
        if (
            set(tag.attrs) != {"data-math-identifier"}
            or tag.get_text() != tag["data-math-identifier"]
            or not re.fullmatch("[A-Za-zА-Яа-я]", tag.get_text())
        ):
            raise UnsupportedCondition("unsupported mathematical variable markup")
        tag.unwrap()
    return soup


def read(context):
    content = context.get("normalized_content") or {}
    condition = section(content, "condition")
    if condition is None:
        raise UnsupportedCondition("a canonical condition is required")
    soup = _visible(BeautifulSoup(str(condition.get("html") or ""), "html.parser"))
    tables = []
    for table in soup.find_all("table"):
        allowed = {
            "table": {"width"},
            "tbody": set(),
            "tr": set(),
            "td": {"width", "data-align", "data-valign"},
            "th": {"data-align", "data-cell-tone"},
            "br": set(),
            "i": set(),
        }
        for tag in [table, *table.find_all(True)]:
            if tag.name not in allowed or not set(tag.attrs) <= allowed[tag.name]:
                raise UnsupportedCondition("unsupported distribution table markup")
        rows = [
            [
                normalize(
                    " ".join(cell.get_text(" ", strip=True).replace("\xad", "").split())
                )
                for cell in row.find_all(["td", "th"], recursive=False)
            ]
            for row in table.find_all("tr")
        ]
        tables.append(rows)
        table.decompose()
    copied = {**condition, "html": str(soup)}
    prepared = {
        **context,
        "normalized_content": {
            **content,
            "sections": [
                copied if s is condition else s for s in content.get("sections", [])
            ],
        },
    }
    _, _, answer, solution, text = require_content(prepared)
    text = normalize(text).replace("−", "-").replace("‑", "-").replace("\u2060", "")
    # Normalize mathematical spacing only; all surrounding prose still full-matches.
    text = re.sub(r"\s*([()=])\s*", r"\1", text)
    return condition, answer, solution, text, tables


def result(value, html, symbol="E(X)"):
    answer = format_answer(Fraction(value))
    return answer, html + line(symbol + "=" + answer.replace(",", "{,}"))


def plan(context, solver):
    condition, answer, solution, text, tables = read(context)
    value, html = solver(text, tables)
    repair = finish(condition, answer, solution, value, html)
    if "\\" not in value:
        return repair
    current = BeautifulSoup(
        str((answer or {}).get("html") or ""), "html.parser"
    ).select("span[data-inline-latex]")
    changes = [
        t
        for t in repair.transformations
        if not t["transformation_target_id"].startswith("section:answer")
    ]
    if len(current) != 1 or current[0]["data-inline-latex"] != value:
        markup = (
            '<p><span data-inline-latex="' + escape(value, quote=True) + '"></span></p>'
        )
        changes.append(rewrite(answer, "answer", "Ответ", markup))
    return replace(repair, transformations=tuple(changes))
