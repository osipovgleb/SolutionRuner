"""Inspect and annotate audited fractional-hyperbola source diagrams."""

from __future__ import annotations

import hashlib
import json
from fractions import Fraction
from pathlib import Path
from xml.etree import ElementTree as ET

from ..core.errors import ContentPlanError
from .diagrams import _n, svg_frame
from .hyperbola import _snap

ASSET_DIR = Path(__file__).parent / "assets/fractional-hyperbolas"
NS = "{http://www.w3.org/2000/svg}"


def graph_evidence(data: bytes) -> dict:
    root = ET.fromstring(data)
    ox, oy, sx, sy, view = svg_frame(data)
    lines = list(root.iter(NS + "line"))
    hs = {
        round(float(n.get("y1")), 3)
        for n in lines
        if n.get("stroke-dasharray")
        and abs(float(n.get("y1")) - float(n.get("y2"))) < 0.01
    }
    vs = {
        round(float(n.get("x1")), 3)
        for n in lines
        if n.get("stroke-dasharray")
        and abs(float(n.get("x1")) - float(n.get("x2"))) < 0.01
    }
    if len(hs) != 1 or len(vs) != 1:
        raise ContentPlanError("need unique horizontal and vertical asymptotes")
    k = _snap((oy - next(iter(hs))) / sy)
    b = _snap((ox - next(iter(vs))) / sx)
    markers = [
        n for n in root.iter(NS + "circle") if n.get("fill", "").upper() == "#143B8F"
    ]
    audit = (
        registry()
        .get("audited_unmarked_graphs", {})
        .get(hashlib.sha256(data).hexdigest())
        if not markers
        else None
    )
    if not markers and not audit:
        raise ContentPlanError(
            "need a marked graph point or audited source grid intersections"
        )
    points = (
        [
            (
                _snap((float(n.get("cx")) - ox) / sx),
                _snap((oy - float(n.get("cy"))) / sy),
            )
            for n in markers
        ]
        if markers
        else [tuple(map(Fraction, p)) for p in audit["points"]]
    )
    x, y = points[0]
    if x + b == 0:
        raise ContentPlanError("marked point is on vertical asymptote")
    c = (x + b) * (y - k)
    if not c or any((px + b) * (py - k) != c for px, py in points):
        raise ContentPlanError("graph points disagree with shifted hyperbola")
    a = c + k * b

    def inside(point):
        px, py = ox + float(point[0]) * sx, oy - float(point[1]) * sy
        return (
            view[0] + 3 < px < view[0] + view[2] - 3
            and view[1] + 3 < py < view[1] + view[3] - 3
        )

    second = next((p for p in points[1:] if p[0] != x), (-2 * b - x, 2 * k - y))
    if not inside(second):
        import math

        candidates = []
        for nx in range(
            math.floor((view[0] - ox) / sx),
            math.ceil((view[0] + view[2] - ox) / sx) + 1,
        ):
            if nx == x or nx + b == 0:
                continue
            ny = k + c / (nx + b)
            if ny.denominator == 1 and inside((nx, ny)):
                candidates.append((Fraction(nx), ny))
        if not candidates:
            raise ContentPlanError("no second visible lattice point")
        second = min(candidates, key=lambda p: (abs(p[0]), abs(p[1])))
    offset = next((p for p in [(c - b, k + 1), (-c - b, k - 1)] if inside(p)), (x, y))
    import math

    candidates = []
    for nx in range(
        math.floor((view[0] - ox) / sx), math.ceil((view[0] + view[2] - ox) / sx) + 1
    ):
        if nx in (x, second[0]) or nx + b == 0:
            continue
        ny = k + c / (nx + b)
        if ny.denominator == 1 and inside((nx, ny)):
            candidates.append((Fraction(nx), ny))
    if not candidates:
        for nx in range(
            math.floor((view[0] - ox) / sx),
            math.ceil((view[0] + view[2] - ox) / sx) + 1,
        ):
            if nx in (x, second[0]) or nx + b == 0:
                continue
            ny = k + c / (nx + b)
            if ny.denominator in (2, 4) and inside((nx, ny)):
                candidates.append((Fraction(nx), ny))
    if not candidates:
        raise ContentPlanError("no third visible grid point")
    third = (
        points[2]
        if audit
        else offset
        if offset in candidates
        else min(candidates, key=lambda p: (abs(p[0]), abs(p[1])))
    )
    return {
        "k": k,
        "a": a,
        "b": b,
        "c": c,
        "point": (x, y),
        "second": second,
        "third": third,
        "offset": offset,
    }


def annotate(data: bytes, method: str) -> bytes:
    if method not in ("points", "offset"):
        raise ValueError(method)
    facts = graph_evidence(data)
    ox, oy, sx, sy, _ = svg_frame(data)
    root = ET.fromstring(data)
    marker = next(
        (n for n in root.iter(NS + "circle") if n.get("fill", "").upper() == "#143B8F"),
        None,
    )
    red = "#D12626"
    nodes = ['<g data-role="fractional-hyperbola-overlay">']
    if method == "points":
        points = [
            (
                "A",
                float(marker.get("cx"))
                if marker is not None
                else ox + float(facts["point"][0]) * sx,
                float(marker.get("cy"))
                if marker is not None
                else oy - float(facts["point"][1]) * sy,
            ),
            (
                "B",
                ox + float(facts["second"][0]) * sx,
                oy - float(facts["second"][1]) * sy,
            ),
            (
                "C",
                ox + float(facts["third"][0]) * sx,
                oy - float(facts["third"][1]) * sy,
            ),
        ]
    else:
        ux, uy = facts["offset"]
        px, py = ox + float(ux) * sx, oy - float(uy) * sy
        nodes.append(
            f'<line x1="{_n(ox - float(facts["b"]) * sx)}" y1="{_n(py)}" x2="{_n(px)}" y2="{_n(py)}" stroke="{red}" stroke-width="1.8"/>'
        )
        points = [("", px, py)]
    for label, px, py in points:
        nodes.append(
            f'<circle cx="{_n(px)}" cy="{_n(py)}" r="{_n((float(marker.get("r")) if marker is not None else 2.5) + 0.5)}" fill="{red}"/>'
        )
        if label:
            nodes.append(
                f'<text x="{_n(px + 6)}" y="{_n(py - 6)}" fill="{red}" font-family="Times New Roman, serif" font-size="11">{label}</text>'
            )
    nodes.append("</g>")
    closing = data.rfind(b"</svg>")
    return data[:closing] + "".join(nodes).encode() + data[closing:]


def registry():
    return json.loads((ASSET_DIR / "source-assets.json").read_text())
