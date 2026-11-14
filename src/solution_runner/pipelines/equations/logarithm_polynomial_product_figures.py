"""Reuse exact source sign charts and prepare only the missing two-point chart."""

import json
from itertools import pairwise
from pathlib import Path
from xml.etree import ElementTree as ET

import sympy as sp
from bs4 import BeautifulSoup

from ..probability import solution_diagrams
from ..probability.common import UnsupportedCondition
from .logarithm_polynomial_product import analyze
from .rational_inequality_figures import read_formula
from .rational_inequality_parser import X
from .rational_inequality_roots import compare, ordered
from .rational_inequality_svg import marker, node, single_canvas

SOURCES = json.loads(
    (
        Path(__file__).parent
        / "assets/logarithmic-inequalities/polynomial-product.json"
    ).read_text()
)
KEY = "polynomial_log_sign_chart"
ALT = "Знаки произведения многочлена и логарифма на исходной области определения"


def plotted(a):
    domain = a.domain
    if (
        not isinstance(domain, sp.Interval)
        or not domain.left_open
        or not domain.right_open
        or sum(p.is_finite for p in (domain.start, domain.end)) != 1
    ):
        raise UnsupportedCondition(
            "the source chart requires one open half-line domain"
        )
    boundary = domain.start if domain.start.is_finite else domain.end
    points = ordered(
        {
            boundary,
            *[p for p in a.stage.points if domain.closure.contains(p) is sp.true],
        }
    )
    signs = []
    for index, (left, right) in enumerate(pairwise((-sp.oo, *points, sp.oo))):
        sample = (
            right - 1
            if left == -sp.oo
            else left + 1
            if right == sp.oo
            else (left + right) / 2
        )
        if domain.contains(sample) is sp.true:
            signs.append((index, compare(a.stage.original.subs(X, sample), 0)))
    return points, tuple(signs)


def signature(a):
    points, signs = plotted(a)
    return {
        "domain": str(a.domain),
        "solution": str(a.solution),
        "points": list(map(str, points)),
        "signs": [list(pair) for pair in signs],
        "closed": [a.solution.contains(p) is sp.true for p in points],
    }


def compatible(entry, a):
    return entry["signature"] == signature(a)


def validate_source(asset, condition, a, role):
    uid = asset.get("asset_id")
    entry = SOURCES["figures"].get(uid)
    shared = (
        isinstance(uid, str)
        and asset.get("asset_key") == "shared_" + uid.replace("-", "")[:16]
    )
    if (
        entry is None
        or entry["role"] != role
        or not compatible(entry, a)
        or asset.get("asset_key")
        not in (entry["asset_key"], "shared_" + uid.replace("-", "")[:16])
        or asset.get("kind", "ordinary_image" if shared else None) != "ordinary_image"
        or asset.get("url", "/assets/" + uid if shared else None) != "/assets/" + uid
        or condition.get("asset_keys")
        or uid in condition["html"]
        or BeautifulSoup(condition["html"], "html.parser").find("img")
    ):
        raise UnsupportedCondition(
            "the exact source chart role, identity and complete plotted mathematics must match"
        )
    return uid


def required_assets(context):
    if any(
        asset.get("asset_key") != KEY
        for asset in context["normalized_content"].get("assets", ())
    ):
        return ()
    a = analyze(read_formula(context)[1])
    matches = [
        uid
        for uid, entry in SOURCES["figures"].items()
        if entry["role"] == "interval_chart" and compatible(entry, a)
    ]
    if len(matches) > 1:
        raise UnsupportedCondition("one compatible source chart must not be duplicated")
    return tuple(
        {"source_asset_id": uid, "section_id": "solution:1", "alt_text": ALT}
        for uid in matches
    )


def render(a):
    points, signs = plotted(a)
    if len(points) != 2 or any(p.is_Integer is not True for p in points):
        raise UnsupportedCondition(
            "only the reviewed missing two-integer chart requires generation"
        )
    root = single_canvas(215.3065, 45.2688, "single", "x")
    root.set("data-source-style", "50a75b8a-8c17-4e31-bc6c-066fdffe71ea")
    positions = (37.5135, 164.5463)
    coords = (0, *positions, 206.3005)
    for index, sign in signs:
        node(
            root,
            "text",
            data_interval=index,
            data_sign=sign,
            x=(coords[index] + coords[index + 1]) / 2,
            y=10,
            text_anchor="middle",
            font_family="Times New Roman,serif",
            font_size=16,
            fill="#143B8F",
        ).text = {1: "+", -1: "−", 0: "0"}[sign]
    for point, x in zip(points, positions, strict=True):
        marker(
            root, point, x, 18.928, a.solution.contains(point) is sp.true, label_y=16.5
        )
    return ET.tostring(root, encoding="unicode")


def selection(context, a):
    content, condition, *_ = read_formula(context)[0]
    if condition.get("asset_keys") or BeautifulSoup(
        condition["html"], "html.parser"
    ).find("img"):
        raise UnsupportedCondition("the reviewed condition has no figures")
    originals = [v for v in content.get("assets", ()) if v.get("asset_key") != KEY]
    if len(originals) > 1:
        raise UnsupportedCondition("only one reviewed interval chart is required")
    if originals:
        return validate_source(originals[0], condition, a, "interval_chart"), None
    return None, render(a)


def diagram_specs(context):
    a = analyze(read_formula(context)[1])
    _, svg = selection(context, a)
    return (solution_diagrams.spec(KEY, svg),) if svg is not None else ()


def chart(context, a, generated):
    uid, svg = selection(context, a)
    if uid and any(v.get("asset_key") == KEY for v in generated):
        raise UnsupportedCondition(
            "an existing exact source chart must not be duplicated"
        )
    html, key, changes = solution_diagrams.image(
        context["normalized_content"],
        KEY,
        ALT,
        source_id=uid,
        svg=svg,
        generated=generated,
    )
    return html, (key,), tuple(changes)
