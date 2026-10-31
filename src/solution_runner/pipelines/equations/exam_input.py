"""Read both complete exam subparts without changing their mathematical markup."""

import re

from bs4 import BeautifulSoup, NavigableString

from ..word_problems.common import UnsupportedCondition, section
from .power_arithmetic import ScalarParser

FIRST = r"Решите уравнение:? ФОРМУЛА[.;]?"
SECOND = r"(?:Найдите его корни на промежутке|Укажите корни, принадлежащие отрезку|Укажите корни этого уравнения, принадлежащее отрезку|Найдите(?: все)? корни уравнения, принадлежащие отрезку|Укажите все корни этого уравнения, принадлежащие промежутку|Найдите решения уравнения, принадлежащие отрезку|Найдите его корни, принадлежащие отрезку|Найдите(?: все)? корни этого уравнения, принадлежащие (?:промежутку|отрезку)|Найдите корни этого уравнения, принадлежащие промежутку|Укажите корни этого уравнения, принадлежащие (?:отрезку|промежутку)|Укажите корни этого уравнения, принадлежащего отрезку|Определите, какие из его корней принадлежат отрезку) ИНТЕРВАЛ\.?"


def read_parts(context):
    content = context.get("normalized_content") or {}
    parts = tuple(section(content, key) for key in ("condition", "answer", "solution"))
    if (
        parts[0] is None
        or content.get("assets")
        or any(s.get("asset_keys") for s in parts if s)
    ):
        raise UnsupportedCondition("canonical exam text without assets is required")
    soup = BeautifulSoup(parts[0]["html"], "html.parser")
    lists = soup.find_all("ol")
    if len(lists) != 1 or lists[0].attrs != {
        "data-layout": "source-subparts",
        "type": "a",
    }:
        raise UnsupportedCondition(
            "exactly one canonical two-part exam list is required"
        )
    if any(
        (isinstance(node, NavigableString) and node.strip())
        or (getattr(node, "name", None) and node.name != "li")
        for node in lists[0].children
    ):
        raise UnsupportedCondition(
            "instructions outside the two subparts are not discarded"
        )
    rows = lists[0].find_all("li", recursive=False)
    if len(rows) != 2 or any(
        r.attrs not in ({"data-list-marker": marker}, {"data-list-marker": alias})
        for r, marker, alias in zip(rows, ("а)", "б)"), ("a)", "b)"))
    ):
        raise UnsupportedCondition("the two exam markers must be a and b in order")
    for sub in rows[1].find_all("sub"):
        before, after = sub.previous_sibling, sub.next_sibling
        if (
            sub.attrs
            or sub.find(True)
            or not re.fullmatch(r"[2-9]\d{0,2}", sub.get_text())
            or not isinstance(before, NavigableString)
            or not str(before).endswith("log")
            or not isinstance(after, NavigableString)
            or not re.match(r"\d", str(after))
        ):
            raise UnsupportedCondition(
                "only explicit numeric logarithm subscripts are supported"
            )
        before.replace_with(str(before)[:-3] + r"\log_")
        sub.replace_with("{" + sub.get_text() + "}")
    for node in soup.find_all(True):
        if node not in [lists[0], *rows] and (
            node.name not in {"span", "nobr"}
            or (node.name == "nobr" and node.attrs)
            or (
                node.name == "span"
                and (
                    set(node.attrs) != {"data-inline-latex"}
                    or node.get_text(strip=True)
                )
            )
        ):
            raise UnsupportedCondition("unknown exam condition markup")
    if any(str(x).strip() and x is not lists[0] for x in soup.contents):
        raise UnsupportedCondition(
            "instructions outside the exam list are not discarded"
        )
    formulas = rows[0].select("span[data-inline-latex]")
    if len(formulas) != 1:
        raise UnsupportedCondition("the first part must contain one equation")
    equation = formulas[0]["data-inline-latex"]
    formulas[0].replace_with("ФОРМУЛА")
    interval_spans = rows[1].select("span[data-inline-latex]")
    for s in interval_spans:
        s.replace_with(s["data-inline-latex"])
    first = " ".join(
        rows[0].get_text(" ", strip=True).replace("\xad", "").replace("ё", "е").split()
    )
    first = re.sub(r"\s+([.,:;])", r"\1", first)
    second = " ".join(
        rows[1]
        .get_text(" ", strip=True)
        .replace("\xad", "")
        .replace("ё", "е")
        .replace("−", "-")
        .split()
    )
    second = re.sub(r"\s+([.,:;])", r"\1", second)
    if not re.fullmatch(FIRST, first):
        raise UnsupportedCondition("the entire equation instruction must match")
    return parts, equation, second


def read(context):
    parts, equation, second = read_parts(context)
    interval, bounds = read_interval(second)
    return parts, equation, interval, bounds


def read_interval(second):
    for old, new in (
        (r"\left[", "["),
        (r"\right]", "]"),
        (r"\left(", "("),
        (r"\right)", ")"),
        (r"\,", ""),
    ):
        second = second.replace(old, new)
    match = re.fullmatch(r"(.+?)\s+([\[(].+[\])])\s*\.?", second)
    if not match or not re.fullmatch(SECOND, match[1] + " ИНТЕРВАЛ"):
        raise UnsupportedCondition(
            "the entire interval-selection instruction must match"
        )
    interval = match[2]
    lower, upper = (endpoint(v) for v in endpoint_texts(interval))
    from .exam_scalar import compare

    ordering = compare(lower, upper)
    if ordering > 0 or (ordering == 0 and (interval[0] != "[" or interval[-1] != "]")):
        raise UnsupportedCondition("a nonempty ordered interval is required")
    return interval, (lower, upper, interval[0] == "[", interval[-1] == "]")


def endpoint_texts(interval):
    inner = interval[1:-1]
    # Semicolons leave unbraced decimal commas inside their scalar endpoints.
    depth = 0
    separators = []
    for i, ch in enumerate(inner):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        elif ch in ";," and depth == 0:
            separators.append(i)
    semicolons = [i for i in separators if inner[i] == ";"]
    separators = semicolons or separators
    if len(separators) != 1:
        raise UnsupportedCondition("the interval must have two unambiguous endpoints")
    i = separators[0]
    return inner[:i], inner[i + 1 :]


def endpoint(text):
    import sympy as sp

    from .power_arithmetic import balanced, clean

    if text.strip().startswith(r"\sqrt{") and r"\log_" in text:
        normalized = clean(re.sub(r"\\log_([2-9])(?=\s)", r"\\log_{\1}", text))
        inner, end = balanced(normalized, 5)
        if end != len(normalized):
            raise UnsupportedCondition(
                "a nested logarithm endpoint must be one complete square root"
            )
        value = endpoint(inner)
        from .exam_scalar import compare

        if compare(value, sp.Integer(0)) < 0:
            raise UnsupportedCondition(
                "a square root endpoint needs a nonnegative argument"
            )
        return sp.Pow(value, sp.Rational(1, 2), evaluate=False)
    if r"\pi" not in text:
        from .logarithm_arithmetic import actual
        from .logarithm_parser import LogarithmParser

        return actual(LogarithmParser(text).parse().value)
    if "p" in text.replace(r"\pi", ""):
        raise UnsupportedCondition(
            "an interval endpoint cannot contain an undeclared variable"
        )
    return (
        ScalarParser(text.replace(r"\pi", "p"), {"p"})
        .parse()
        .subs(sp.Symbol("p", real=True), sp.pi)
    )


def repair(parts, answer, answer_html, html):
    from ..word_problems.common import RepairPlan, rewrite

    condition, ans, solution = parts
    transformations = []
    for item, key, title, expected in (
        (ans, "answer", "Ответ", answer_html),
        (solution, "solution", "Решение", html),
    ):
        if item is None or item.get("html") != expected:
            transformations.append(rewrite(item, key, title, expected))
    return RepairPlan(answer, condition["html"], html, tuple(transformations))
