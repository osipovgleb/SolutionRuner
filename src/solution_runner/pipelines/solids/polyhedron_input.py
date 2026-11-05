"""Read complete solid conditions, preserving explicit vertex sequences and footers."""

import re

from bs4 import BeautifulSoup, Tag

from ..core.errors import ContentPlanError
from .box_coordinates import HEADER, VERTEX
from .box_geometry_input import LETTERS, text


def sequence(raw):
    if re.fullmatch(rf"(?:{VERTEX}){{1,8}}", raw) is None:
        return None
    names = tuple(re.findall(VERTEX, raw))
    return names if len(set(names)) == len(names) else None


def complete_text(html, source=None):
    if not isinstance(html, str):
        raise ContentPlanError("one complete polyhedron condition is required")
    soup = BeautifulSoup(html, "html.parser")
    identifiers = set()
    for tag in soup.find_all(["var", "i", "em"]):
        label = tag.get_text().translate(LETTERS)
        sub = tag.next_sibling
        while isinstance(sub, str) and not sub.strip():
            sub = sub.next_sibling
        if isinstance(sub, Tag) and sub.name == "sub":
            label += "_1"
        if sequence(label):
            identifiers.add(label)
    raw = text(html, source, extra_identifiers=tuple(identifiers)).replace(r"\,", " ")
    # Adjacent explicit chunks can jointly name the header or a pyramid/prism.
    raw = re.sub(r"(?<=[A-D1])\s+(?=[A-D])", "", raw)
    return raw


def vertices(raw):
    if "," not in raw:
        names = sequence(raw)
    else:
        parts = tuple(v.strip() for v in raw.split(","))
        names = parts if all(re.fullmatch(VERTEX, v) for v in parts) else None
    if names is None or len(names) not in (4, 5, 6) or len(set(names)) != len(names):
        raise ContentPlanError(
            "one explicit list of four to six distinct solid vertices is required"
        )
    return names


FIRST = rf"Найдите объем многогранника, вершинами которого являются (?:точки|вершины)\s+(.+?)\s+(прямоугольного\s+)?параллелепипеда\s+{HEADER}\s*,\s*у которого\s+(.+?)\s*\."
SECOND = rf"[ВB] прямоугольном параллелепипеде\s+{HEADER}\s+известно, что\s+(.+?)\s*\.\s*Найдите объем многогранника, вершинами которого являются (?:точки|вершины)\s+(.+?)\s*\."
PRISM = rf"Дан прямоугольный параллелепипед\s+{HEADER}\s*,\s*длины его ребер\s+(.+?)\s*\.\s*Найдите объем призмы\s+(.+?)\s*\."
TOTAL = rf"Объем параллелепипеда\s+{HEADER}\s+равен\s+(.+?)\s*\.\s*Найдите объем треугольной пирамиды\s+(.+?)\s*\."


def read_condition(html, source=None):
    raw = complete_text(html, source)
    footer = " Параллелепипед прямоугольный."
    rectangular = raw.endswith(footer)
    if rectangular:
        raw = raw[: -len(footer)]
    match = re.fullmatch(FIRST, raw)
    if match:
        points, explicit, given = match.groups()
        if not explicit and not rectangular:
            raise ContentPlanError(
                "three edge lengths alone do not determine an oblique parallelepiped volume"
            )
        return vertices(points), "edges", given, None
    for pattern, kind in ((SECOND, None), (PRISM, "prism"), (TOTAL, "pyramid")):
        match = re.fullmatch(pattern, raw)
        if match:
            given, points = match.groups()
            return (
                vertices(points),
                "total" if pattern == TOTAL else "edges",
                given,
                kind,
            )
    raise ContentPlanError(
        "one complete supported polyhedron-volume condition is required"
    )
