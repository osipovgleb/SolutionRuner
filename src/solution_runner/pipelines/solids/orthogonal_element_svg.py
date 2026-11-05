"""Keep exact numerical source art and add only reviewed parent helper constructions."""

import base64
import hashlib
import json
from importlib.resources import files
from itertools import combinations

from lxml import etree

from ..core.errors import ContentPlanError
from .orthogonal_element_sources import DATA as SOURCE_DATA
from .orthogonal_element_sources import source_bytes

SVG = "http://www.w3.org/2000/svg"
XLINK = "http://www.w3.org/1999/xlink"
DATA = json.loads(
    files(__package__).joinpath("assets/orthogonal_element_diagrams.json").read_text()
)


def intersection(a, b, c, d):
    ux, uy = b[0] - a[0], b[1] - a[1]
    vx, vy = d[0] - c[0], d[1] - c[1]
    denominator = ux * vy - uy * vx
    if abs(denominator) < 1e-9:
        raise ContentPlanError("the reviewed image construction has parallel lines")
    t = ((c[0] - a[0]) * vy - (c[1] - a[1]) * vx) / denominator
    return (a[0] + t * ux, a[1] + t * uy)


def anchors(review):
    points = dict(review["points"])
    for name, construction in review.get("constructions", {}).items():
        if "translation" in construction:
            points[name] = tuple(
                sum(
                    weight * points[key][i]
                    for key, weight in construction["translation"]
                )
                for i in (0, 1)
            )
        else:
            points[name] = intersection(
                *(points[n] for edge in construction["intersection"] for n in edge)
            )
    return points


def line(root, a, b, width, dashed):
    attributes = {
        "x1": f"{a[0]:.6f}",
        "y1": f"{a[1]:.6f}",
        "x2": f"{b[0]:.6f}",
        "y2": f"{b[1]:.6f}",
        "fill": "none",
        "stroke": "#143B8F",
        "stroke-width": str(width),
        "stroke-linecap": "round",
        "stroke-linejoin": "round",
    }
    if dashed:
        attributes["stroke-dasharray"] = f"{10 * width},{4 * width}"
    etree.SubElement(root, "{" + SVG + "}line", attributes)


def canvas(review, raw):
    if review["format"] == "svg":
        root = etree.fromstring(
            raw, etree.XMLParser(resolve_entities=False, no_network=True)
        )
        for recolor in review.get("recolor", []):
            matches = [
                n
                for n in root.iter("{" + SVG + "}line")
                if all(n.get(k) == v for k, v in recolor.items())
            ]
            if len(matches) != 1:
                raise ContentPlanError("the exact reviewed hidden SVG edge changed")
            matches[0].set("stroke", "#143B8F")
        return root
    w, h = review["canvas"]
    root = etree.Element(
        "{" + SVG + "}svg",
        nsmap={None: SVG, "xlink": XLINK},
        width=str(w),
        height=str(h),
        viewBox=f"0 0 {w} {h}",
    )
    etree.SubElement(
        root,
        "{" + SVG + "}image",
        {
            "width": str(w),
            "height": str(h),
            "{" + XLINK + "}href": "data:image/png;base64,"
            + base64.b64encode(raw).decode("ascii"),
        },
    )
    return root


def overlay(root, review):
    group = etree.SubElement(root, "{" + SVG + "}g")
    if not review.get("protect"):
        return group
    w, h = review["canvas"]
    definitions = etree.SubElement(root, "{" + SVG + "}defs")
    clip = etree.SubElement(
        definitions,
        "{" + SVG + "}clipPath",
        id="orthogonal-helper-clip",
        clipPathUnits="userSpaceOnUse",
    )
    path = f"M0 0 H{w} V{h} H0 Z"
    for x, y, width, height in review["protect"]:
        path += f" M{x} {y} V{y + height} H{x + width} V{y} Z"
    etree.SubElement(
        clip,
        "{" + SVG + "}path",
        d=path,
        **{"fill-rule": "evenodd", "clip-rule": "evenodd"},
    )
    group.set("clip-path", "url(#orthogonal-helper-clip)")
    return group


def render(source, model):
    key = source + ":" + model.mode + ":" + model.requested
    review = DATA.get(key)
    raw = source_bytes(source)
    if not review or hashlib.sha256(raw).hexdigest() != review["sha256"]:
        raise ContentPlanError("the complete numerical helper diagram needs review")
    figure = SOURCE_DATA["figures"][source]
    if model.kind != figure["kind"] or model.given != figure["given"]:
        raise ContentPlanError(
            "the numerical image dimensions differ from the named model"
        )
    triangle = (
        (model.names[0], model.right, model.names[1])
        if model.mode in {"distance", "distance_squared"}
        else model.names
    )
    edges = (
        [s["ends"] for s in review["segments"]]
        + review.get("existing_segments", [])
        + review.get("recolored_segments", [])
    )
    if {frozenset(e) for e in edges} != {
        frozenset(e) for e in combinations(triangle, 2)
    }:
        raise ContentPlanError(
            "the helper paths do not show the actual parent triangle"
        )
    root = canvas(review, raw)
    points = anchors(review)
    group = overlay(root, review)
    for segment in review["segments"]:
        a, b = segment["ends"]
        if a not in model.points or b not in model.points:
            raise ContentPlanError("a drawn helper is absent from the named geometry")
        if "split" in segment:
            middle = intersection(
                points[a], points[b], *(points[n] for n in segment["split"])
            )
            line(group, points[a], middle, review["stroke_width"], False)
            line(group, middle, points[b], review["stroke_width"], True)
        else:
            line(group, points[a], points[b], review["stroke_width"], segment["dashed"])
    for name, (dx, dy) in review.get("labels", {}).items():
        x, y = points[name]
        node = etree.SubElement(
            root,
            "{" + SVG + "}text",
            x=str(x + dx),
            y=str(y + dy),
            fill="#0D0F0F",
            **{
                "font-family": "Times New Roman, Times, serif",
                "font-size": str(review["font_size"]),
                "font-style": "italic",
            },
        )
        node.text = name
    return etree.tostring(root, encoding="unicode")
