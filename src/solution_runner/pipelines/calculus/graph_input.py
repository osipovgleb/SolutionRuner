"""Checksum-bound graph evidence shared by calculus graph questions."""

import hashlib
import json
import re
from copy import deepcopy
from pathlib import Path

import sympy as sp
from bs4 import BeautifulSoup

from ..probability import condition_diagram, solution_diagrams
from ..probability.common import UnsupportedCondition
from .common import X, polynomial, read

ASSETS = Path(__file__).with_name("assets")
EVIDENCE = json.loads((ASSETS / "graph_evidence.json").read_text())
KEY = "tangent_triangle"
ALT = "Касательная и прямоугольный треугольник для вычисления её наклона"


def _read_text(context):
    prepared = deepcopy(context)
    condition = next(
        s for s in prepared["normalized_content"]["sections"] if s["key"] == "condition"
    )
    soup = BeautifulSoup(condition["html"], "html.parser")
    for tag in soup.find_all("sub"):
        if tag.parent.name == "sub":
            continue
        if (
            tag.attrs
            or tag.get_text() != "0"
            or any(
                child.name != "sub" or child.attrs or child.find(True)
                for child in tag.find_all(True)
            )
        ):
            raise UnsupportedCondition("only the source x-zero subscript is supported")
        tag.replace_with("_0")
    condition["html"] = str(soup)
    cond, ans, solution, text = read(prepared)
    text = re.sub(r"\s*([=()])\s*", r"\1", text)
    text = re.sub(r"x\s*_\{?0\}?", "x_0", text)
    return prepared["normalized_content"], cond, ans, solution, text


def read_graph(context):
    return condition_diagram.read(context, EVIDENCE, ASSETS, content_reader=_read_text)


def tangent(entry):
    if "equation" in entry:
        expression = polynomial(entry["equation"], X)
        if sp.Poly(expression, X).degree() != 1:
            raise UnsupportedCondition(
                "the labelled tangent must be a nonconstant straight line"
            )
    else:
        p, q = (tuple(sp.Rational(n) for n in xy) for xy in entry["line_points"])
        if p[0] == q[0]:
            raise UnsupportedCondition("a vertical tangent has no finite derivative")
        expression = p[1] + (q[1] - p[1]) / (q[0] - p[0]) * (X - p[0])
    return sp.expand(expression)


def contact(entry):
    point = {key: sp.Rational(value) for key, value in entry.get("contact", {}).items()}
    expression = tangent(entry)
    if "x" in point:
        y = expression.subs(X, point["x"])
        if "y" in point and point["y"] != y:
            raise UnsupportedCondition("the marked contact point is not on its tangent")
        point["y"] = y
    elif "y" in point:
        slope = sp.diff(expression, X)
        if slope == 0:
            raise UnsupportedCondition(
                "the ordinate does not determine a unique contact abscissa"
            )
        point["x"] = (point["y"] - expression.subs(X, 0)) / slope
    return point


def requirements(entry):
    asset = entry.get("solution_asset")
    return (
        (
            {
                "source_asset_id": asset["source_id"],
                "section_id": "solution:1",
                "alt_text": entry.get("solution_alt", ALT),
            },
        )
        if asset
        else ()
    )


def figure(content, entry, *, svg=None, generated=()):
    asset = entry.get("solution_asset")
    key = entry.get("diagram_key", KEY)
    if (
        asset
        and hashlib.sha256(
            (ASSETS / (asset["source_id"] + ".svg")).read_bytes()
        ).hexdigest()
        != asset["sha256"]
    ):
        raise UnsupportedCondition("the audited solution triangle has changed")
    allowed = {
        a["asset_id"]
        for a in content["assets"]
        if a["asset_key"]
        in next(s for s in content["sections"] if s["key"] == "condition")["asset_keys"]
    }
    allowed.update(
        [asset["source_id"]]
        if asset
        else [
            a["source_asset_id"]
            for a in generated
            if svg is not None
            and a.get("asset_key") == key
            and a.get("sha256") == solution_diagrams.spec(key, svg)["sha256"]
        ]
    )
    if any(a["asset_id"] not in allowed for a in content["assets"]):
        raise UnsupportedCondition("an unrelated graph solution asset is present")
    if not asset and svg is None:
        return "", None, ()
    return solution_diagrams.image(
        content,
        key,
        entry.get("solution_alt", ALT),
        source_id=asset["source_id"] if asset else None,
        svg=svg,
        generated=generated,
    )
