"""Read actual apex, center, midpoint, edge and requested segment names."""

import re

from ..core.errors import ContentPlanError
from .pyramid_model import base_volume, center_area, measured


def _square(raw):
    match = re.fullmatch(
        r"[ВB] правильной четырехугольной пирамиде SABCD точка O\s*[—–-]\s*центр основания, S\s*[—–-]?\s*вершина,\s*(.+?)\. Найдите (?:боковое ребро|длину отрезка)\s+([A-DSO]{2})\.",
        raw,
    )
    if not match:
        return None
    givens = re.fullmatch(
        r"(SO|S[A-D]|AC|BD)\s*=\s*(.+?)\s*,+\s*(SO|S[A-D]|AC|BD)\s*=\s*(.+)", match[1]
    )
    if not givens:
        raise ContentPlanError("two complete pyramid segment assignments are required")
    fields = lambda label: (
        "H" if label == "SO" else "D" if label in {"AC", "BD"} else "e"
    )
    labels = (givens[1], givens[3])
    keys = tuple(fields(n) for n in labels)
    target = match[2]
    if len(set(keys)) != 2 or target not in {"SO", "AC", "BD", "SA", "SB", "SC", "SD"}:
        raise ContentPlanError("independent named pyramid dimensions are required")
    kind = {"H": "named_height", "D": "named_diagonal", "e": "named_edge"}[
        fields(target)
    ]
    return measured(
        kind, "square", (givens[2], givens[4]), keys, fields(target), (*labels, target)
    )


def _midpoint(raw):
    match = re.fullmatch(
        r"[ВB] правильной треугольной пирамиде SABC\s*(?:точка )?([LMNQR])\s*[—–-]\s*середина ребра\s+([ABC]{2})\s*, S\s*[—–-]\s*вершина\. Известно, что\s+(.+?)\. Найдите\s+(.+?)\.",
        raw,
    )
    if not match:
        return None
    point, edge, assignments, question = match.groups()
    if len(set(edge)) != 2:
        raise ContentPlanError("a genuine base edge midpoint is required")
    slant = "S" + point
    surface = re.fullmatch(
        r"([ABC]{2})\s*=\s*(.+?)\s*, а\s*" + slant + r"\s*=\s*(.+)", assignments
    )
    names = (point, edge)
    if surface and question == "площадь боковой поверхности":
        if len(set(surface[1])) != 2:
            raise ContentPlanError("a base edge is required")
        return measured(
            "triangle_lateral",
            "triangle",
            (surface[2], surface[3]),
            ("a", "l"),
            "L",
            (*names, surface[1], slant),
        )
    inverse = re.fullmatch(
        r"([A-Z]{2})\s*=\s*(.+?)\s*, а площадь боковой поверхности равна\s+(.+)",
        assignments,
    )
    if not inverse:
        raise ContentPlanError("complete apothem and lateral-area data are required")
    requested = re.fullmatch(r"длину отрезка\s+([A-Z]{2})", question)
    if requested is None:
        raise ContentPlanError("one actual requested segment is required")
    if inverse[1] in {"AB", "BA", "BC", "CB", "AC", "CA"} and requested[1] == slant:
        return measured(
            "triangle_apothem",
            "triangle",
            (inverse[2], inverse[3]),
            ("a", "L"),
            "l",
            (*names, inverse[1], slant),
        )
    if inverse[1] == slant and requested[1] in {"AB", "BA", "BC", "CB", "AC", "CA"}:
        return measured(
            "triangle_side",
            "triangle",
            (inverse[2], inverse[3]),
            ("l", "L"),
            "a",
            (*names, requested[1], slant),
        )
    raise ContentPlanError("the midpoint and actual apothem do not match the question")


def _center(raw):
    match = re.fullmatch(
        r"[ВB] правильной треугольной пирамиде SABC медианы основания пересекаются в точке ([MNOP])\.\s*(.+)",
        raw,
    )
    if not match:
        return None
    point, tail = match.groups()
    edge = rf"(?:{point}S|S{point})"
    patterns = (
        (
            "center_height",
            rf"Площадь треугольника ABC равна\s+(.+?)\s*, объем пирамиды равен\s+(.+?)\. Найдите длину отрезка\s+({edge})\.",
            "H",
        ),
        (
            "center_volume",
            rf"Площадь треугольника ABC равна\s+(.+?)\s*,\s*({edge})\s*=\s*(.+?)\. Найдите объем пирамиды\.",
            "V",
        ),
        (
            "center_area",
            rf"Объем пирамиды равен\s+(.+?)\s*,\s*({edge})\s*=\s*(.+?)\. Найдите площадь треугольника ABC\.",
            "B",
        ),
    )
    for kind, pattern, target in patterns:
        m = re.fullmatch(pattern, tail)
        if m:
            if target == "H":
                return base_volume(kind, (m[1], m[2]), "area", "H", (point, m[3]))
            if target == "V":
                return base_volume(kind, (m[1], m[3]), "area", "V", (point, m[2]))
            return center_area((m[1], m[3]), (point, m[2]))
    raise ContentPlanError("complete center-height-area-volume data are required")


def read(raw):
    return _square(raw) or _midpoint(raw) or _center(raw)
