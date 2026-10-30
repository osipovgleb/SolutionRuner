"""Uniform forward walks on checksum-verified trees drawn with SVG nodes and edges."""

import json
import re
from collections import defaultdict
from fractions import Fraction
from pathlib import Path
from xml.etree import ElementTree as ET

from . import condition_diagram, solution_diagrams
from .bernoulli import fmt, result
from .common import UnsupportedCondition, line

_ASSETS = Path(__file__).with_name("assets")
_EVIDENCE = json.loads((_ASSETS / "park_diagrams.json").read_text())
_TARGETS = {
    "пруду или фонтану": ("fountain", "pond"),
    "детской площадке": ("playground",),
}
_TITLES = {"fountain": "фонтану", "pond": "пруду", "playground": "детской площадке"}
_PATTERN = re.compile(
    r"Артем гуляет по парку\. Он выходит из точки S и, дойдя до очередной развилки, с равными шансами выбирает следующую дорожку, но не возвращается обратно\. Найдите вероятность того, что таким образом он выйдет к (?P<target>"
    + "|".join(_TARGETS)
    + r")\."
)
_KEY = "generated_park_routes"
_ALT = "Пути к выбранным местам парка и вероятности выбора дорожек"


def svg_graph(source):
    root = ET.fromstring(source)
    if any(n.get("transform") for n in root.iter()):
        raise UnsupportedCondition(
            "graph nodes and edges must share one coordinate system"
        )
    circles = [n for n in root.iter() if n.tag.endswith("circle")]
    points = [(Fraction(n.get("cx")), Fraction(n.get("cy"))) for n in circles]
    if not points or len(set(points)) != len(points):
        raise UnsupportedCondition("graph nodes must be distinct")
    edges = []
    for node in root.iter():
        if not node.tag.endswith("line"):
            continue
        ends = []
        for suffix in ("1", "2"):
            x, y = Fraction(node.get("x" + suffix)), Fraction(node.get("y" + suffix))
            matches = [
                i
                for i, (px, py) in enumerate(points)
                if (px - x) ** 2 + (py - y) ** 2 <= Fraction(9, 4)
            ]
            if len(matches) != 1:
                raise UnsupportedCondition(
                    "a drawn edge endpoint does not select one node"
                )
            ends.append(matches[0])
        edges.append(tuple(ends))
    return root, points, tuple(edges)


def forward_paths(node_count, edges, start):
    if not 0 <= start < node_count or len(edges) != node_count - 1:
        raise UnsupportedCondition("the supported forward walk requires a tree")
    adjacency = [set() for _ in range(node_count)]
    for a, b in edges:
        if (
            not 0 <= a < node_count
            or not 0 <= b < node_count
            or a == b
            or b in adjacency[a]
        ):
            raise UnsupportedCondition("invalid or duplicate graph edge")
        adjacency[a].add(b)
        adjacency[b].add(a)
    reached = set()
    rows = []

    def visit(node, parent, path, factors):
        if node in reached:
            raise UnsupportedCondition("the forward walk graph contains a cycle")
        reached.add(node)
        choices = sorted(adjacency[node] - {parent})
        if not choices:
            rows.append((node, path, factors))
            return
        for nxt in choices:
            visit(nxt, node, path + (nxt,), factors + (Fraction(1, len(choices)),))

    visit(start, None, (start,), ())
    if len(reached) != node_count:
        raise UnsupportedCondition("the forward walk graph is disconnected")
    return tuple(rows)


def _input(context):
    content, condition, answer, solution, text, entry, source = condition_diagram.read(
        context, _EVIDENCE, _ASSETS
    )
    match = _PATTERN.fullmatch(text)
    if match is None:
        raise UnsupportedCondition("unsupported complete forward-walk condition")
    root, points, edges = svg_graph(source)
    rows = forward_paths(len(points), edges, entry["start"])
    destinations = {int(k): v for k, v in entry["destinations"].items()}
    if set(destinations) != {leaf for leaf, _, _ in rows}:
        raise UnsupportedCondition(
            "every terminal graph node needs an audited destination"
        )
    targets = _TARGETS[match["target"]]
    return (
        content,
        condition,
        answer,
        solution,
        entry,
        source,
        root,
        points,
        edges,
        rows,
        destinations,
        targets,
    )


def _overlay(entry, targets):
    return next(
        (
            a["asset_id"]
            for a in entry["overlays"]
            if set(a["destinations"]) == set(targets)
        ),
        None,
    )


def required_assets(context):
    *_, entry, _source, _root, _points, _edges, _rows, _destinations, targets = _input(
        context
    )
    source = _overlay(entry, targets)
    return (
        ({"source_asset_id": source, "section_id": "solution:1", "alt_text": _ALT},)
        if source
        else ()
    )


def build_context_repair_plan(context, *, condition_asset_bytes=None):
    (
        content,
        condition,
        answer_section,
        solution,
        entry,
        source,
        _root,
        _points,
        _edges,
        rows,
        destinations,
        targets,
    ) = _input(context)
    condition_diagram.verify_download(source, condition_asset_bytes)
    html = "<p>На каждой развилке Артем равновероятно выбирает одну из дорожек, кроме той, по которой пришёл. Вероятность конкретного пути равна произведению вероятностей этих выборов. Разные пути к нужным местам несовместны, поэтому их вероятности складываются.</p>"
    figure, key, changes = solution_diagrams.image(
        content, _KEY, _ALT, source_id=_overlay(entry, targets)
    )
    value = Fraction(0)
    terms = []
    for target_index, target in enumerate(targets):
        groups = defaultdict(list)
        for leaf, path, factors in rows:
            if destinations[leaf] == target:
                groups[path[:-1]].append(factors)
        html += f"<p>Пути к {_TITLES[target]}:</p>"
        for _, variants in sorted(groups.items()):
            choices = [f"1 из {p.denominator}" for p in variants[0][:-1] if p != 1]
            choices.append(f"{len(variants)} из {variants[0][-1].denominator}")
            html += (
                "<p>На последовательных развилках выбираем подходящие дорожки: "
                + ", ".join(choices)
                + ".</p>"
            )
            factors = variants[0][:-1] + (sum(v[-1] for v in variants),)
            probability = Fraction(1)
            for factor in factors:
                probability *= factor
            value += probability
            terms.append(fmt(probability))
            html += line(
                "P_"
                + str(len(terms))
                + "="
                + (r"\cdot ".join(fmt(f) for f in factors if f != 1) or "1")
                + "="
                + fmt(probability)
            )
        if target_index == 0:
            html += figure
    html += "<p>Сложим вероятности найденных путей:</p>" + line(
        "P=" + "+".join(terms) + "=" + fmt(value)
    )
    answer, html = result(value, html)
    return solution_diagrams.repair(
        condition, answer_section, solution, answer, html, (key,), changes
    )
