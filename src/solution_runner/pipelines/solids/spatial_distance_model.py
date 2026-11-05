"""Read complete proof-and-distance questions using existing solid dimensions."""

import re
from dataclasses import dataclass, field

import sympy as sp
from bs4 import BeautifulSoup

from ..core.errors import ContentPlanError
from . import box_coordinates as c
from . import (
    prism_separation_model,
    spatial_altitude_model,
    spatial_metric_model,
    spatial_plane_model,
)
from .box_distance_model import read_question as read_box
from .measurements import positive
from .prism_input import text
from .pyramid_model import regular

MODES = (
    {
        "box_altitude_comparison",
        "pyramid_skew_midpoint",
    }
    | spatial_metric_model.MODES
    | spatial_plane_model.MODES
    | spatial_altitude_model.MODES
    | prism_separation_model.MODES
)
SEG = c.SEGMENT
VERTEX = c.VERTEX
BOX = (
    rf"Длины ребер ({SEG}), ({SEG}) и ({SEG}) прямоугольного параллелепипеда {c.HEADER} равны соответственно (.+?), (.+?) и (.+?)\. "
    rf"Докажите, что расстояние от вершины ({VERTEX}) до прямой ({SEG}) больше, чем расстояние от вершины ({VERTEX}) до прямой ({SEG})\. "
    rf"Найдите расстояние от вершины ({VERTEX}) до прямой ({SEG})\."
)
PYRAMID = r"[ВB] правильной четырехугольной пирамиде SABCD "
GIVENS = (
    (
        r"сторона AB основания равна (.+?), а высота SH пирамиды равна (.+?)\.",
        ("a", "H"),
    ),
    (r"боковое ребро SA равно (.+?), а высота SH пирамиды равна (.+?)\.", ("e", "H")),
    (r"сторона основания AB\s*=\s*(.+?), а боковое ребро SA\s*=\s*(.+?)\.", ("a", "e")),
)
MIDPOINTS = r" Точки M и N [—–-] середины ребер CD и AB,? соответственно"
ALTITUDE = (
    r", а NT [—–-] высота пирамиды (?:NSCD )?с вершиной N и основанием SCD\.",
    r"\. Точка N [—–-] вершина пирамиды NSCD, NT [—–-] ее высота\.",
)
REQUEST = (
    r" Докажите, что точка T (?:является серединой SM|делит SM пополам)\. "
    r"Найдите расстояние между (?:прямыми )?NT и SC\."
)


@dataclass(frozen=True)
class SpatialDistance:
    mode: str
    given: tuple[tuple[str, sp.Expr], ...]
    q: dict[str, sp.Expr]
    names: tuple[str, ...]
    answer: sp.Expr
    squares: tuple[sp.Expr, ...] = ()
    symbols: dict[str, str] = field(default_factory=dict)


def condition_text(html, source):
    soup = BeautifulSoup(html, "html.parser")
    lists = soup.find_all(["ol", "ul"])
    if len(lists) > 1:
        raise ContentPlanError("one canonical two-part spatial question is required")
    if lists:
        listing = lists[0]
        items = listing.find_all("li", recursive=False)
        if (
            listing.name != "ol"
            or listing.attrs != {"data-layout": "source-subparts", "type": "a"}
            or len(items) != 2
            or [i.attrs for i in items]
            != [{"data-list-marker": "а)"}, {"data-list-marker": "б)"}]
            or len(listing.find_all("li")) != 2
            or any(str(v).strip() for v in listing.contents if v not in items)
        ):
            raise ContentPlanError("the source proof and distance subparts changed")
        for item in items:
            item.name, item.attrs = "p", {}
        listing.unwrap()
    letters = str.maketrans(
        {"М": "M", "Т": "T", "О": "O", "Н": "H", "Р": "P", "К": "K"}
    )
    for tag in soup.find_all("i"):
        if not tag.attrs and not tag.find(True):
            tag.string = tag.get_text().translate(letters)
    return text(str(soup), source, labels="ABCDEFOSHNMTEPLQKαγ")


def _box(match):
    tokens = match.groups()
    given = tuple(
        (name, positive(v)) for name, v in zip(tokens[:3], tokens[3:6], strict=True)
    )
    if any(len(c.axes(name)) != 1 for name, _ in given):
        raise ContentPlanError("three named box edges are required")
    squares = c.dimensions(given)
    first, line, p, hyp, target, requested = tokens[6:]
    ends = c.endpoints(line)
    if (
        p not in ends
        or first == p
        or target != p
        or set(c.endpoints(hyp)) != {first, *set(ends) - {p}}
        or set(c.endpoints(requested)) != set(c.endpoints(hyp))
    ):
        raise ContentPlanError(
            "the compared distances must share the stated right triangle"
        )
    last = next(v for v in ends if v != p)
    cathetus = first + p
    if len(c.axes(cathetus)) != 1 or set(c.axes(cathetus)) & set(c.axes(p + last)):
        raise ContentPlanError(
            "the comparison requires an edge perpendicular to the opposite face"
        )
    leg = sp.sqrt(c.squared_length(p + last, squares))
    cat = sp.sqrt(c.squared_length(cathetus, squares))
    diagonal = sp.sqrt(c.squared_length(first + last, squares))
    q = {"leg": leg, "cathetus": cat, "hyp": diagonal}
    return SpatialDistance(
        "box_altitude_comparison",
        given,
        q,
        (p, first, last),
        sp.simplify(cat * leg / diagonal),
        squares,
    )


def _pyramid(groups, fields):
    values = tuple(positive(v) for v in groups)
    q = regular("square", dict(zip(fields, values, strict=True)))
    if sp.simplify(q["l"] - q["a"]) != 0:
        raise ContentPlanError(
            "the given pyramid does not prove that T is the midpoint of SM"
        )
    q.update(ST=q["l"] / 2, MC=q["a"] / 2)
    return SpatialDistance(
        "pyramid_skew_midpoint",
        tuple(zip(fields, values, strict=True)),
        q,
        ("S", "M", "N", "T"),
        sp.simplify(q["l"] * q["a"] / (4 * q["e"])),
    )


def read_question(html, source=None):
    if "Докажите" not in BeautifulSoup(html, "html.parser").get_text().replace(
        "\xad", ""
    ):
        return read_box(html, source)
    raw = condition_text(html, source)
    match = re.fullmatch(BOX, raw)
    if match:
        return _box(match)
    for given, fields in GIVENS:
        for altitude in ALTITUDE:
            match = re.fullmatch(PYRAMID + given + MIDPOINTS + altitude + REQUEST, raw)
            if match:
                return _pyramid(match.groups(), fields)
    metric = spatial_metric_model.read(raw)
    if metric is not None:
        return metric
    plane = spatial_plane_model.read(raw)
    if plane is not None:
        return plane
    for reader in (spatial_altitude_model.read, prism_separation_model.read):
        found = reader(raw)
        if found is not None:
            return found
    return read_box(html, source)
