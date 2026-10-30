"""Vector identities with the geometric proofs used by their source families."""

import hashlib
import json
import re
from pathlib import Path

import sympy as sp
from bs4 import BeautifulSoup

from solution_runner.pipelines.core.numbers import format_answer
from solution_runner.pipelines.probability import condition_diagram, solution_diagrams
from solution_runner.pipelines.probability.common import (
    UnsupportedCondition,
    line,
    require_content,
)

from .metric_relations import _VALUE, measure

_ASSETS = Path(__file__).with_name("assets")
_EVIDENCE = json.loads((_ASSETS / "geometry_diagrams.json").read_text())
_CONSTRUCTION = "bad4a4d9-58e9-4e17-8350-fe93b2d69d41"
_ALT = "Треугольник ABC достроен до ромба ABDC"
_RECTANGLE = re.compile(
    rf"Две стороны (?:изображенного на рисунке )?прямоугольника ABCD равны (?P<a>{_VALUE}) и (?P<b>{_VALUE})\. (?:(?:Диагонали пересекаются в точке O\.)\s*)?(?P<ask>Найдите .+)"
)
_RHOMBUS = re.compile(
    rf"Диагонали (?:изображенного на рисунке )?ромба ABCD (?:(?:пересекаются в точке O и равны)|равны) (?P<a>{_VALUE}) и (?P<b>{_VALUE})\. (?P<ask>Найдите .+)"
)
_TRIANGLE = re.compile(
    rf"Стороны правильного треугольника ABC равны (?P<a>{_VALUE})\. (?P<ask>Найдите .+)"
)
_RIGHT = re.compile(
    rf"В прямоугольном треугольнике ABC катет AC равен (?P<a>{_VALUE})\. (?P<ask>Найдите .+)"
)
_VEC = r"\\overrightarrow\{{(?P<{}>[A-DO]{{2}})\}}"
_IDENTITIES = {
    "AB+AD": "AC",
    "AB-AD": "DB",
    "AB-AC": "CB",
    "AO+BO": "AD",
    "AO-BO": "AB",
    "AO+DO": "AB",
    "AO-DO": "AD",
}


def _read(context):
    content = context.get("normalized_content") or {}
    sections = content.get("sections", [])
    original = next((s for s in sections if s.get("key") == "condition"), None)
    if original is None:
        raise UnsupportedCondition("a canonical geometric condition is required")
    soup = BeautifulSoup(original["html"], "html.parser")
    for node in soup.find_all("var"):
        if (
            set(node.attrs) != {"data-math-identifier"}
            or node.get_text() != node["data-math-identifier"]
            or node.get_text() not in {"ABC", "ABCD", "AC", "O", "A", "B", "C", "D"}
        ):
            raise UnsupportedCondition("unsupported geometric identifier markup")
        node.unwrap()
    copied = {**original, "html": str(soup)}
    clean = {
        **context,
        "normalized_content": {
            **content,
            "sections": [copied if s is original else s for s in sections],
        },
    }
    if original.get("asset_keys"):
        *_, text, _entry, _source = condition_diagram.read(clean, _EVIDENCE, _ASSETS)
    else:
        _, _, _, _, text = require_content(
            {
                **clean,
                "normalized_content": {**clean["normalized_content"], "assets": []},
            }
        )
    for asset in content.get("assets", []):
        entry = _EVIDENCE.get(asset.get("asset_id"))
        if entry is None:
            raise UnsupportedCondition(
                "the geometric figure needs a mathematical audit"
            )
        source = (_ASSETS / (asset["asset_id"] + entry["extension"])).read_bytes()
        if hashlib.sha256(source).hexdigest() != entry["sha256"]:
            raise UnsupportedCondition("the audited geometric figure has changed")
    answer = next((s for s in sections if s.get("key") == "answer"), None)
    solution = next((s for s in sections if s.get("key") == "solution"), None)
    return content, original, answer, solution, text


def _question(text):
    for word, operator in (("суммы", "+"), ("разности", "-")):
        match = re.fullmatch(
            rf"Найдите длину {word} векторов "
            + _VEC.format("a")
            + " и "
            + _VEC.format("b")
            + r"\.",
            text,
        )
        if match:
            return "length", match["a"] + operator + match["b"]
    match = re.fullmatch(r"Найдите длину вектора (.+)\.", text)
    if match:
        expression = re.sub(r"\\overrightarrow\{([A-DO]{2})\}", r"\1", match[1])
        if re.fullmatch(r"[A-DO]{2}(?:[+-][A-DO]{2})?", expression):
            return "length", expression
    match = re.fullmatch(
        r"Найдите скалярное произведение (?:векторов )?"
        + _VEC.format("a")
        + r"(?: и |\s*\\cdot\s*)"
        + _VEC.format("b")
        + r"\.",
        text,
    )
    if match:
        return "dot", match["a"] + "*" + match["b"]
    raise UnsupportedCondition("unsupported complete geometric vector question")


def _input(context):
    content, condition, answer, solution, text = _read(context)
    for kind, pattern in (
        ("rectangle", _RECTANGLE),
        ("rhombus", _RHOMBUS),
        ("equilateral", _TRIANGLE),
        ("right", _RIGHT),
    ):
        match = pattern.fullmatch(text)
        if match:
            a = measure(match["a"])
            b = measure(match["b"]) if "b" in match.groupdict() else None
            if a.is_positive is not True or b is not None and b.is_positive is not True:
                raise UnsupportedCondition("all geometric lengths must be positive")
            mode, expression = _question(match["ask"])
            target = _IDENTITIES.get(expression, expression)
            directional = mode == "length" and (
                kind == "rhombus"
                and target in {"AC", "DB"}
                or kind == "rectangle"
                and target in {"AB", "AD"}
            )
            if (directional or kind == "right") and not condition.get("asset_keys"):
                raise UnsupportedCondition(
                    "the geometric roles require their audited figure"
                )
            for asset in content.get("assets", []):
                shape = _EVIDENCE[asset["asset_id"]]["shape"]
                if shape != kind and not (
                    kind == "equilateral" and shape == "equilateral_construction"
                ):
                    raise UnsupportedCondition(
                        "the geometric figure does not match the condition"
                    )
            if "изображенного" in text and not condition.get("asset_keys"):
                raise UnsupportedCondition(
                    "the depicted geometric roles need their audited figure"
                )
            return content, condition, answer, solution, kind, a, b, mode, expression
    raise UnsupportedCondition("unsupported complete geometric vector condition")


def required_assets(context):
    *_, kind, _a, _b, mode, expression = _input(context)
    if kind == "equilateral" and mode == "length" and expression == "AB+AC":
        return (
            {
                "source_asset_id": _CONSTRUCTION,
                "section_id": "solution:1",
                "alt_text": _ALT,
            },
        )
    return ()


def _identity(expression):
    target = _IDENTITIES.get(expression, expression if len(expression) == 2 else None)
    if target is None:
        raise UnsupportedCondition("the geometric vector identity is not supported")
    label = re.sub(r"([A-DO]{2})", r"\\overrightarrow{\1}", expression)
    return target, line(
        label + rf"=\overrightarrow{{{target}}}"
    ) if expression != target else ""


def _exact(value):
    value = sp.simplify(value)
    if value.is_Rational is not True:
        raise UnsupportedCondition("the exact geometric answer is not rational")
    return format_answer(value)


def _quadrilateral(kind, a, b, mode, expression):
    f = sp.latex
    if mode == "dot":
        expected = "AO*BO" if kind == "rhombus" else "AB*AD"
        if expression != expected:
            raise UnsupportedCondition(
                "the dot product does not describe the perpendicular directions"
            )
        explanation = (
            "Диагонали ромба перпендикулярны."
            if kind == "rhombus"
            else "Соседние стороны прямоугольника перпендикулярны."
        )
        html = f"<p>{explanation} Скалярное произведение равно произведению длин на косинус угла между векторами:</p>"
        x, y = expression.split("*")
        html += line(
            rf"\overrightarrow{{{x}}}\cdot\overrightarrow{{{y}}}=|\overrightarrow{{{x}}}|\,|\overrightarrow{{{y}}}|\cos90^{{\circ}}=0"
        )
        return sp.Integer(0), html
    target, identity = _identity(expression)
    html = (
        "<p>Используем правило сложения или вычитания векторов:</p>" + identity
        if identity
        else ""
    )
    if kind == "rhombus" and target in {"AD", "CB", "AB"}:
        value = sp.sqrt(a * a + b * b) / 2
        html += "<p>Диагонали ромба перпендикулярны и делятся точкой пересечения пополам. Сторона — гипотенуза прямоугольного треугольника с катетами, равными половинам диагоналей:</p>"
        html += line(
            rf"{target}=\sqrt{{\left(\frac{{{f(a)}}}{{2}}\right)^2+\left(\frac{{{f(b)}}}{{2}}\right)^2}}"
        )
        html += line(
            rf"{target}=\sqrt{{{f(a * a / 4)}+{f(b * b / 4)}}}={f(sp.simplify(value))}"
        )
    elif kind == "rectangle" and target in {"AC", "DB"}:
        value = sp.sqrt(a * a + b * b)
        html += "<p>Полученный вектор лежит на диагонали прямоугольника. По теореме Пифагора:</p>"
        html += line(
            rf"{target}=\sqrt{{({f(a)})^2+({f(b)})^2}}=\sqrt{{{f(a * a + b * b)}}}"
        )
        html += line(rf"{target}={f(sp.simplify(value))}")
    elif (
        kind == "rhombus"
        and target in {"AC", "DB"}
        or kind == "rectangle"
        and target in {"AB", "AD"}
    ):
        long = target in {"AC", "AD"}
        value = sp.Max(a, b) if long else sp.Min(a, b)
        role = "большей" if long else "меньшей"
        html += (
            f"<p>На рисунке {target} соответствует {role} из данных длин:</p>"
            + line(rf"{target}={f(value)}")
        )
    else:
        raise UnsupportedCondition("the requested geometric segment is not supported")
    return value, html


def _triangle(content, kind, a, mode, expression):
    f = sp.latex
    keys = ()
    if mode == "dot" and expression == "AB*AC":
        if kind == "right":
            value = a * a
            html = (
                "<p>Пусть α — угол между гипотенузой AB и катетом AC. Выразим гипотенузу через катет:</p>"
                + line(r"AB=\frac{AC}{\cos\alpha}")
            )
            html += (
                "<p>Подставим это выражение в определение скалярного произведения:</p>"
                + line(
                    r"\overrightarrow{AB}\cdot\overrightarrow{AC}=AB\cdot AC\cos\alpha=\frac{AC}{\cos\alpha}\cdot AC\cos\alpha=AC^2"
                )
            )
        else:
            value = a * a / 2
            html = (
                "<p>Углы правильного треугольника равны 60°. Используем определение скалярного произведения:</p>"
                + line(
                    r"\overrightarrow{AB}\cdot\overrightarrow{AC}=AB\cdot AC\cos60^{\circ}"
                )
            )
        html += line(
            rf"\overrightarrow{{AB}}\cdot\overrightarrow{{AC}}=({f(a)})^2"
            + (r"\cdot\frac12" if kind == "equilateral" else "")
            + "="
            + f(sp.simplify(value))
        )
    elif kind == "equilateral" and mode == "length" and expression == "AB-AC":
        value = a
        html = (
            "<p>Разность векторов с общим началом равна вектору, соединяющему их концы:</p>"
            + line(r"\overrightarrow{AB}-\overrightarrow{AC}=\overrightarrow{CB}")
        )
        html += "<p>В правильном треугольнике все стороны равны:</p>" + line(
            rf"|\overrightarrow{{CB}}|=CB={f(a)}"
        )
    elif kind == "equilateral" and mode == "length" and expression == "AB+AC":
        value = a * sp.sqrt(3)
        html = (
            "<p>Достроим треугольник до ромба. По правилу параллелограмма:</p>"
            + line(r"\overrightarrow{AB}+\overrightarrow{AC}=\overrightarrow{AD}")
        )
        figure, key, _ = solution_diagrams.image(
            content, "construction", _ALT, source_id=_CONSTRUCTION
        )
        keys = (key,)
        html += figure
        html += (
            "<p>Большая диагональ AD равна удвоенной медиане правильного треугольника ABC:</p>"
            + line(r"h=\frac{AB\sqrt3}{2}")
        )
        html += line(
            rf"AD=2h=2\cdot\frac{{({f(a)})\sqrt3}}{{2}}=({f(a)})\sqrt3={f(sp.simplify(value))}"
        )
    else:
        raise UnsupportedCondition("unsupported geometric triangle vector operation")
    return value, html, keys


def build_context_repair_plan(context):
    content, condition, answer, solution, kind, a, b, mode, expression = _input(context)
    if kind in {"rectangle", "rhombus"}:
        value, html = _quadrilateral(kind, a, b, mode, expression)
        keys = ()
    else:
        value, html, keys = _triangle(content, kind, a, mode, expression)
    return solution_diagrams.repair(
        condition, answer, solution, _exact(value), html, keys
    )
