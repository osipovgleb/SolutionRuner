"""Read a whole calculation question and its explicit scalar conditions."""

import re
from dataclasses import dataclass, field

from bs4 import BeautifulSoup

from ..probability.common import UnsupportedCondition
from ..triangles.isosceles.planner import _normalized_content, _section
from .expression_condition import _FORMULA, read_math_markup
from .power_arithmetic import ScalarParser, clean


@dataclass
class Parameters:
    bindings: dict = field(default_factory=dict)
    positive: set = field(default_factory=set)
    nonzero: set = field(default_factory=set)
    definition: str | None = None


def _parameters(text):
    result = Parameters()
    if not text:
        return result
    definition = re.fullmatch(r"g\(x\)=(.+)", clean(text))
    if definition:
        result.definition = clean(text)
        return result
    for part in re.split(r",\s*(?=[a-z]\s*(?:=|\\gt|>|\\ne|!=))|\s+и\s+", text):
        part = clean(part)
        match = re.fullmatch(
            r"(?P<name>[a-z])(?P<relation>=|\\gt|>|\\ne|!=)(?P<value>.+)", part
        )
        if match is None:
            raise UnsupportedCondition("unsupported complete calculation constraint")
        name, relation = match["name"], match["relation"]
        value = ScalarParser(match["value"]).parse()
        if name in result.bindings or name in result.positive or name in result.nonzero:
            raise UnsupportedCondition("duplicate or conflicting variable constraints")
        if relation == "=":
            if value.is_real is not True or value.free_symbols:
                raise UnsupportedCondition("assigned values must be exact real scalars")
            result.bindings[name] = value
        elif value != 0:
            raise UnsupportedCondition("the supported symbolic domain boundary is zero")
        elif relation in (r"\gt", ">"):
            result.positive.add(name)
        else:
            result.nonzero.add(name)
    return result


def _superscripts(context):
    content = _normalized_content(context)
    condition = _section(content, "condition")
    soup = BeautifulSoup(condition["html"], "html.parser")
    for tag in soup.find_all(True):
        if tag.name not in {"p", "nobr", "sup"} or tag.attrs:
            raise UnsupportedCondition("unsupported superscript power markup")
    for sup in soup.find_all("sup"):
        exponent = sup.get_text()
        if not re.fullmatch(r"[+-]?\d+(?:[,.]\d+)?", exponent):
            raise UnsupportedCondition("unsupported visible superscript exponent")
        sup.replace_with("^{" + exponent + "}")
    text = " ".join(soup.get_text().replace("\xad", "").split())
    match = re.fullmatch(r"Найдите значение выражения:?\s+(.+)\.", text)
    if match is None:
        raise UnsupportedCondition("unsupported complete superscript power question")
    return content, condition, match[1].replace("·", r"\cdot"), Parameters()


def read_calculation(context):
    content = _normalized_content(context)
    condition = _section(content, "condition")
    if condition is None or content.get("assets") or condition.get("asset_keys"):
        raise UnsupportedCondition("calculations require a text-only condition")
    if "<sup" in condition["html"]:
        content, condition, expression, parameters = _superscripts(context)
    else:
        content, condition, formulas, text = read_math_markup(context, indexed=True)
        pattern = rf"(?:Найдите значение выражения|Вычислите):? {_FORMULA}0(?:,? (?:при|если) (?P<constraints>.+?))?\.?"
        match = re.fullmatch(pattern, text)
        if match is None or not formulas:
            raise UnsupportedCondition("unsupported complete calculation question")
        expression = formulas[0].removesuffix(".")
        tail = match["constraints"] or ""
        for index, formula in enumerate(formulas[1:], 1):
            marker = _FORMULA + str(index)
            if tail.count(marker) != 1:
                raise UnsupportedCondition(
                    "an unparsed mathematical declaration remains"
                )
            tail = tail.replace(marker, formula)
        parameters = _parameters(tail)
    return (
        content,
        condition,
        _section(content, "answer"),
        _section(content, "solution"),
        expression,
        parameters,
    )
