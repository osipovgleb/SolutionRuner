"""Exact arithmetic for explicitly given planar vectors and linear expressions."""

import math
import re
from dataclasses import dataclass
from fractions import Fraction

from solution_runner.pipelines.core.numbers import (
    format_answer,
    format_latex_fraction,
    parse_rational,
)
from solution_runner.pipelines.probability.common import (
    NUMBER,
    UnsupportedCondition,
    finish,
    line,
    require_content,
)

_SIGNED = rf"[−–-]?{NUMBER}"
_DECL = re.compile(
    rf"\\(?:vec|overrightarrow)\{{(?P<name>[a-z])\}}\s*=?\s*\(\s*(?P<x>{_SIGNED})\s*;\s*(?P<y>{_SIGNED})\s*\)"
)
_GIVEN = re.compile(r"Даны векторы (?P<decl>.+)\. Найдите (?P<ask>.+)\.")
_SINGLE = re.compile(r"Найдите длину вектора (?P<expr>.+), если (?P<decl>.+)\.")
_TOKEN = re.compile(
    r"\\(?:vec|overrightarrow)\{[a-z]\}|\\frac\{\d+\}\{[1-9]\d*\}|\d+(?:\.\d+)?|\\cdot|[()+*−–-]"
)


def _fmt(value):
    if isinstance(value, tuple):
        return "(" + ";".join(format_latex_fraction(v) for v in value) + ")"
    return format_latex_fraction(value)


@dataclass(frozen=True)
class Value:
    data: object
    latex: str


def _combine(a, b, op, trace):
    av, bv = a.data, b.data
    at = isinstance(av, tuple)
    bt = isinstance(bv, tuple)
    if op in ("+", "-"):
        if at != bt:
            raise UnsupportedCondition("cannot add a scalar and a vector")
        sign = 1 if op == "+" else -1
        value = (
            tuple(x + sign * y for x, y in zip(av, bv, strict=True))
            if at
            else av + sign * bv
        )
        numeric = _fmt(av) + op + _fmt(bv)
    elif at and bt:
        value = sum((x * y for x, y in zip(av, bv, strict=True)), Fraction(0))
        numeric = "+".join(
            rf"\left({_fmt(x)}\right)\cdot\left({_fmt(y)}\right)"
            for x, y in zip(av, bv, strict=True)
        )
    elif at or bt:
        vector, scalar = (av, bv) if at else (bv, av)
        value = tuple(scalar * x for x in vector)
        numeric = _fmt(av) + r"\cdot " + _fmt(bv)
    else:
        value = av * bv
        numeric = _fmt(av) + r"\cdot " + _fmt(bv)
    label = "(" + a.latex + (r"\cdot " if op == "*" else op) + b.latex + ")"
    result = Value(value, label)
    trace.append((label, numeric, value))
    return result


def evaluate(expression, vectors):
    expression = (
        expression.replace("{,}", ".")
        .replace(",", ".")
        .replace("−", "-")
        .replace("–", "-")
    )
    expression = expression.replace(r"\left", "").replace(r"\right", "")
    tokens = []
    offset = 0
    while offset < len(expression):
        if expression[offset].isspace():
            offset += 1
            continue
        match = _TOKEN.match(expression, offset)
        if match is None:
            raise UnsupportedCondition("unsupported vector expression token")
        tokens.append(match.group())
        offset = match.end()
    if not tokens or len(tokens) > 50:
        raise UnsupportedCondition("empty or oversized vector expression")
    position = 0
    trace = []

    def factor():
        nonlocal position
        if position >= len(tokens):
            raise UnsupportedCondition("missing vector expression operand")
        token = tokens[position]
        position += 1
        if token in ("+", "-"):
            result = factor()
            return (
                result
                if token == "+"
                else _combine(Value(Fraction(-1), "-1"), result, "*", trace)
            )
        if token == "(":
            result = expression_sum()
            if position >= len(tokens) or tokens[position] != ")":
                raise UnsupportedCondition("unbalanced vector expression")
            position += 1
            return result
        if token.startswith((r"\vec", r"\overrightarrow")):
            name = token[token.index("{") + 1 : -1]
            if name not in vectors:
                raise UnsupportedCondition("the expression uses an undefined vector")
            return Value(vectors[name], token)
        if token[0].isdigit() or token.startswith(r"\frac"):
            return Value(parse_rational(token), token)
        raise UnsupportedCondition("unexpected vector expression operand")

    def term():
        nonlocal position
        result = factor()
        while position < len(tokens):
            token = tokens[position]
            if token in ("*", r"\cdot"):
                position += 1
            elif token == "(" or token.startswith((r"\vec", r"\overrightarrow")):
                pass
            else:
                break
            result = _combine(result, factor(), "*", trace)
        return result

    def expression_sum():
        nonlocal position
        result = term()
        while position < len(tokens) and tokens[position] in ("+", "-"):
            op = tokens[position]
            position += 1
            result = _combine(result, term(), op, trace)
        return result

    value = expression_sum()
    if position != len(tokens):
        raise UnsupportedCondition("unconsumed vector expression")
    return value.data, tuple(trace)


def exact_root(value):
    if value < 0:
        raise UnsupportedCondition("a squared vector length cannot be negative")
    numerator, denominator = math.isqrt(value.numerator), math.isqrt(value.denominator)
    if (
        numerator * numerator != value.numerator
        or denominator * denominator != value.denominator
    ):
        raise UnsupportedCondition(
            "the requested answer requires an unsupported irrational form"
        )
    return Fraction(numerator, denominator)


def _declarations(text):
    vectors = {}
    end = 0
    for match in _DECL.finditer(text):
        gap = text[end : match.start()]
        if gap not in ("", ", ", " и "):
            raise UnsupportedCondition("unsupported vector declaration separator")
        name = match["name"]
        if name in vectors:
            raise UnsupportedCondition("a vector is declared more than once")
        vectors[name] = tuple(
            parse_rational(match[k].replace("−", "-").replace("–", "-"))
            for k in ("x", "y")
        )
        end = match.end()
    if end != len(text) or not 1 <= len(vectors) <= 3:
        raise UnsupportedCondition("unsupported complete vector declarations")
    return vectors


def _ask(text):
    if text == "косинус угла между ними":
        return "cosine", None
    for phrase, mode in [
        ("длину вектора ", "length"),
        ("квадрат длины вектора ", "square"),
        ("сумму координат вектора ", "sum"),
        ("значение выражения ", "scalar"),
        ("скалярное произведение ", "scalar"),
    ]:
        if text.startswith(phrase):
            expression = text.removeprefix(phrase)
            if expression.startswith("векторов "):
                parts = expression.removeprefix("векторов ").split(" и ")
                if len(parts) != 2:
                    raise UnsupportedCondition("two vector operands are required")
                expression = "(" + parts[0] + r")\cdot(" + parts[1] + ")"
            return mode, expression
    raise UnsupportedCondition("unsupported complete coordinate-vector question")


def build_context_repair_plan(context):
    _, condition, answer_section, solution, text = require_content(context)
    match = _GIVEN.fullmatch(text)
    single = _SINGLE.fullmatch(text) if match is None else None
    if match is None and single is None:
        raise UnsupportedCondition("unsupported complete coordinate-vector condition")
    vectors = _declarations((match or single)["decl"])
    mode, expression = _ask(match["ask"]) if match else ("length", single["expr"])
    html = "<p>Действия над векторами выполняем по соответствующим координатам:</p>"
    if mode == "scalar":
        html += (
            "<p>Скалярное произведение равно сумме произведений соответствующих координат:</p>"
            + line(r"\vec u\cdot\vec v=u_xv_x+u_yv_y")
        )
    if mode == "cosine":
        if len(vectors) != 2:
            raise UnsupportedCondition(
                "two vectors are required for their mutual angle"
            )
        a, b = vectors.values()
        na = sum(x * x for x in a)
        nb = sum(x * x for x in b)
        if not na or not nb:
            raise UnsupportedCondition("an angle with the zero vector is undefined")
        dot = sum(x * y for x, y in zip(a, b, strict=True))
        denominator = exact_root(na * nb)
        value = dot / denominator
        html += line(r"\vec a\cdot\vec b=x_ax_b+y_ay_b")
        html += line(
            r"\vec a\cdot\vec b="
            + "+".join(
                rf"({_fmt(x)})\cdot({_fmt(y)})" for x, y in zip(a, b, strict=True)
            )
            + "="
            + _fmt(dot)
        )
        html += line(
            rf"|\vec a|=\sqrt{{{_fmt(na)}}},\quad |\vec b|=\sqrt{{{_fmt(nb)}}}"
        )
        html += line(
            rf"\cos\alpha=\frac{{\vec a\cdot\vec b}}{{|\vec a||\vec b|}}=\frac{{{_fmt(dot)}}}{{{_fmt(denominator)}}}={_fmt(value)}"
        )
    else:
        computed, trace = evaluate(expression, vectors)
        if trace:
            html += "<p>Найдём координаты промежуточных векторов и выполним указанные действия:</p>"
            for label, numeric, result in trace:
                html += line(label + "=" + numeric + "=" + _fmt(result))
        if mode == "scalar":
            if isinstance(computed, tuple):
                raise UnsupportedCondition("the question requires a scalar result")
            value = computed
        else:
            if not isinstance(computed, tuple):
                raise UnsupportedCondition("the question requires a vector")
            if not trace:
                html += line(expression + "=" + _fmt(computed))
            if mode == "sum":
                value = sum(computed)
                html += "<p>Сложим полученные координаты:</p>" + line(
                    "S="
                    + "+".join("(" + _fmt(x) + ")" for x in computed)
                    + "="
                    + _fmt(value)
                )
            else:
                square = sum(x * x for x in computed)
                html += "<p>Квадрат длины — сумма квадратов координат:</p>" + line(
                    r"|\vec v|^2="
                    + "+".join("(" + _fmt(x) + ")^2" for x in computed)
                    + "="
                    + _fmt(square)
                )
                value = square if mode == "square" else exact_root(square)
                if mode == "length":
                    html += line(rf"|\vec v|=\sqrt{{{_fmt(square)}}}={_fmt(value)}")
    answer = format_answer(value)
    return finish(condition, answer_section, solution, answer, html)
