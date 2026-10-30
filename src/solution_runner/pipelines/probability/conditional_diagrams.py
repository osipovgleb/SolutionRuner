"""Conditional events on audited point diagrams and weighted experiment trees."""

import json
import re
from fractions import Fraction
from pathlib import Path
from xml.etree import ElementTree as ET

from . import condition_diagram
from .bernoulli import checked, fmt, result
from .common import UnsupportedCondition, finish, line

_ASSETS = Path(__file__).with_name("assets")
_EVIDENCE = json.loads((_ASSETS / "conditional_diagrams.json").read_text())
_SIGNED = r"-?\d+(?:\.\d+)?"
_POINT = re.compile(
    rf"M(?P<x>{_SIGNED})[,\s]*(?P<y>{_SIGNED})c(?P<shape>-1\.2882,0-2\.3386,1\.0457-2\.3386,2\.3386|-1\.928,0-3\.5,1\.565-3\.5,3\.5)c"
)
_UNIFORM = re.compile(
    r"На диаграмме Эйлера показаны события A и B в некотором случайном эксперименте, в котором (?P<n>\d+) равновозможных элементарных событий\. Элементарные события показаны точками\. Найдите P\((?P<want>[AB])\\mid (?P<given>[AB])\) [—–-] условную вероятность события (?P=want) при условии (?P=given)\."
)
_SET = r"[a-d](?:, [a-d])*(?: и [a-d])?"
_TREE = re.compile(
    rf"На рисунке показано дерево некоторого случайного эксперимента\. Событию A благоприятствуют элементарные события (?P<aset>{_SET}), а событию B благоприятствуют элементарные события (?P<bset>{_SET})\. Найдите P\((?P<want>[AB])\\mid (?P<given>[AB])\) [—–-] условную вероятность события (?P=want) при условии (?P=given)\."
)


def uniform_points(source):
    root = ET.fromstring(source)
    if any(n.get("transform") for n in root.iter()):
        raise UnsupportedCondition(
            "the audited point coordinates must share one coordinate system"
        )
    ellipses = [
        n for n in root.iter() if n.tag.endswith("ellipse") and n.get("fill") != "none"
    ]
    if len(ellipses) != 2:
        raise UnsupportedCondition("two event ellipses are required")
    events = {"A": set(), "B": set()}
    points = []
    for node in root.iter():
        if not node.tag.endswith("path") or node.get("fill") == "none":
            continue
        match = _POINT.match(node.get("d", ""))
        if match is None:
            continue
        radius = Fraction("2.3386" if match["shape"].startswith("-1.2882") else "3.5")
        x = Fraction(match["x"])
        y = Fraction(match["y"]) + radius
        index = len(points)
        points.append((x, y))
        for label, ellipse in zip(events, ellipses, strict=True):
            cx, cy, rx, ry = (
                Fraction(ellipse.get(k)) for k in ("cx", "cy", "rx", "ry")
            )
            distance = ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2
            if distance == 1:
                raise UnsupportedCondition(
                    "an elementary outcome lies on an event boundary"
                )
            if distance < 1:
                events[label].add(index)
    if not points:
        raise UnsupportedCondition("no audited elementary outcomes were found")
    return tuple(Fraction(1, len(points)) for _ in points), events


def tree_weights(branches):
    if len(branches) != 3 or any(len(row) != 2 for row in branches):
        raise UnsupportedCondition("the audited tree must have two binary levels")
    rows = [tuple(checked(Fraction(p)) for p in row) for row in branches]
    if any(sum(row) != 1 for row in rows):
        raise UnsupportedCondition("outgoing branch probabilities must sum to one")
    first, left, right = rows
    return (
        first[0] * left[0],
        first[0] * left[1],
        first[1] * right[0],
        first[1] * right[1],
    )


def conditional_probability(weights, want, given):
    if not weights or sum(weights) != 1 or any(p < 0 or p > 1 for p in weights):
        raise UnsupportedCondition(
            "elementary weights must define a probability distribution"
        )
    if not (set(want) | set(given)) <= set(range(len(weights))):
        raise UnsupportedCondition("an event names an unknown elementary outcome")
    denominator = sum((weights[i] for i in given), Fraction(0))
    if denominator == 0:
        raise UnsupportedCondition("the conditioning event has zero probability")
    numerator = sum((weights[i] for i in set(want) & set(given)), Fraction(0))
    return numerator / denominator, numerator, denominator


def _input(context):
    content, condition, answer, solution, text, entry, source = condition_diagram.read(
        context, _EVIDENCE, _ASSETS
    )
    if len(content["assets"]) != 1:
        raise UnsupportedCondition(
            "conditional-event rules only support the condition diagram"
        )
    if entry["kind"] == "uniform_points":
        match = _UNIFORM.fullmatch(text)
        if match is None:
            raise UnsupportedCondition("unsupported complete point-diagram condition")
        weights, events = uniform_points(source)
        if len(weights) != int(match["n"]):
            raise UnsupportedCondition("the stated count disagrees with the diagram")
    else:
        match = _TREE.fullmatch(text)
        if match is None:
            raise UnsupportedCondition("unsupported complete weighted-tree condition")
        weights = tree_weights(entry["branches"])
        events = {
            name: {
                ord(letter) - ord("a") for letter in re.findall("[a-d]", match[field])
            }
            for name, field in [("A", "aset"), ("B", "bset")]
        }
    return (
        condition,
        answer,
        solution,
        entry,
        source,
        weights,
        events,
        match["want"],
        match["given"],
    )


def build_context_repair_plan(context, *, condition_asset_bytes=None):
    condition, answer_section, solution, entry, source, weights, events, want, given = (
        _input(context)
    )
    condition_diagram.verify_download(source, condition_asset_bytes)
    html = "<p>По рисунку найдём вероятности элементарных событий и событий A и B.</p>"
    if entry["kind"] == "binary_tree":
        branches = entry["branches"]
        for i, p in enumerate(weights):
            top = Fraction(branches[0][i // 2])
            bottom = Fraction(branches[1 + i // 2][i % 2])
            html += line(rf"P({chr(97 + i)})={fmt(top)}\cdot {fmt(bottom)}={fmt(p)}")
    else:
        html += f"<p>Все {len(weights)} точек равновозможны. Внутри A находятся {len(events['A'])} точек, внутри B — {len(events['B'])}, в общей части — {len(events['A'] & events['B'])}.</p>"
    for label, indices in events.items():
        terms = (
            rf"\frac{{{len(indices)}}}{{{len(weights)}}}"
            if entry["kind"] == "uniform_points"
            else ("+".join(fmt(weights[i]) for i in sorted(indices)) or "0")
        )
        html += line(
            rf"P({label})="
            + terms
            + "="
            + fmt(sum((weights[i] for i in indices), Fraction(0)))
        )
    value, numerator, denominator = conditional_probability(
        weights, events[want], events[given]
    )
    html += line(rf"P({want}\cap {given})={fmt(numerator)}")
    html += "<p>Подставим найденные значения в формулу условной вероятности:</p>"
    html += line(
        rf"P({want}\mid {given})=\frac{{P({want}\cap {given})}}{{P({given})}}=\frac{{{fmt(numerator)}}}{{{fmt(denominator)}}}={fmt(value)}"
    )
    answer, html = result(value, html)
    return finish(condition, answer_section, solution, answer, html)
