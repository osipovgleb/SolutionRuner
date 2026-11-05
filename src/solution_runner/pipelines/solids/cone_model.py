"""Compute exact cone dimensions and requested quantities from the actual givens."""

import re
from dataclasses import dataclass

import sympy as sp

from ..core.errors import ContentPlanError
from ..probability.common import UnsupportedCondition
from .cone_input import text
from .measurements import positive


@dataclass(frozen=True)
class ConeQuantity:
    mode: str
    kind: str
    given: tuple[sp.Expr, ...]
    answer: sp.Expr
    input_kind: str = ""
    radius: sp.Expr = sp.S.Zero
    height: sp.Expr = sp.S.Zero
    slant: sp.Expr = sp.S.Zero
    ratio: sp.Expr = sp.S.One


SETUPS = (
    (
        "height_slant",
        r"Высота конуса равна\s+(.+?)\s*,\s*(?:а длина образующей\s*(?:равна|[—–−-])|образующая равна)\s*(.+?)\s*\.",
    ),
    (
        "height_diameter",
        r"Высота конуса равна\s+(.+?)\s*,\s*а диаметр основания\s*(?:равен|[—–−-])\s*(.+?)\s*\.",
    ),
    (
        "diameter_slant",
        r"Диаметр основания конуса равен\s+(.+?)\s*,\s*а длина образующей\s*(?:равна|[—–−-])\s*(.+?)\s*\.",
    ),
    (
        "radius_height",
        r"Радиус основания конуса равен\s+(.+?)\s*,\s*высота равна\s+(.+?)\s*\.",
    ),
    (
        "base_height",
        r"Площадь основания конуса равна\s+(.+?)\s*,\s*высота\s*(?:равна|[—–−-])\s*(.+?)\s*\.",
    ),
    (
        "circumference_slant",
        r"Длина окружности основания конуса равна\s+(.+?)\s*,\s*образующая равна\s+(.+?)\s*\.",
    ),
)
QUESTIONS = (
    ("volume", r"Найдите его объем, деленный на\s+\\pi\s*\."),
    (
        "total",
        r"Найдите площадь (?:его )?полной поверхности(?: конуса)?, деленную на\s+\\pi\s*\.",
    ),
    ("slant", r"Найдите образующую конуса\s*\."),
    ("height", r"Найдите высоту конуса\s*\."),
    ("diameter", r"Найдите диаметр основания конуса\s*\."),
    ("axial", r"Найдите площадь осевого сечения (?:этого )?конуса\s*\."),
    ("lateral", r"Найдите площадь боковой поверхности конуса\s*\."),
)


def _from_radius_height(r, h):
    return r, h, sp.sqrt(h * h + r * r)


def _from_radius_slant(r, l):
    return r, sp.sqrt(l * l - r * r), l


def _from_height_slant(h, l):
    return sp.sqrt(l * l - h * h), h, l


DIMENSIONS = {
    "height_slant": _from_height_slant,
    "height_diameter": lambda h, d: _from_radius_height(d / 2, h),
    "diameter_slant": lambda d, l: _from_radius_slant(d / 2, l),
    "radius_height": _from_radius_height,
    "base_height": lambda area, h: _from_radius_height(sp.sqrt(area / sp.pi), h),
    "circumference_slant": lambda circumference, l: _from_radius_slant(
        circumference / (2 * sp.pi), l
    ),
    "slant_angle": lambda l, angle: _from_height_slant(l / 2, l),
    "diameter_apex": lambda d, angle: _from_radius_height(d / 2, d / 2),
    "rotation": lambda leg, angle: _from_radius_height(leg, leg),
}


TARGETS = {
    "height_slant": {"volume", "total", "diameter", "axial"},
    "height_diameter": {"slant"},
    "diameter_slant": {"height", "axial"},
    "radius_height": {"total"},
    "base_height": {"axial"},
    "circumference_slant": {"lateral"},
    "slant_angle": {"volume"},
    "diameter_apex": {"volume"},
    "rotation": {"volume"},
}


def geometry(input_kind, given, target):
    values = tuple(positive(s, pi=True) for s in given)
    if target not in TARGETS.get(input_kind, ()):
        raise ContentPlanError("this cone input and target combination needs review")
    if input_kind == "slant_angle" and values[1] != 30:
        raise ContentPlanError(
            "this parent uses the explicit 30-degree cathetus property"
        )
    if input_kind == "diameter_apex" and values[1] != 90:
        raise ContentPlanError("the axial apex must be explicitly right")
    r, h, l = DIMENSIONS[input_kind](*values)
    if any(v.is_real is not True or v.is_positive is not True for v in (r, h, l)):
        raise ContentPlanError("positive nondegenerate cone dimensions are required")
    answers = {
        "volume": r * r * h / 3,
        "total": r * (r + l),
        "slant": l,
        "height": h,
        "diameter": 2 * r,
        "axial": r * h,
        "lateral": sp.pi * r * l,
    }
    return ConeQuantity(
        "geometry", target, values, sp.simplify(answers[target]), input_kind, r, h, l
    )


def _special(raw):
    match = re.fullmatch(
        r"Найдите объем V конуса, образующая которого равна\s+(.+?)\s+и наклонена к плоскости основания под углом\s*(.+?)°\. В ответе укажите\s+\\frac\{V\}\{\\pi\}\s*\.",
        raw,
    )
    if match:
        return geometry("slant_angle", match.groups(), "volume")
    match = re.fullmatch(
        r"Диаметр основания конуса равен\s+(.+?)\s*, а угол при вершине осевого сечения равен\s*(.+?)°\. Вычислите объем конуса, деленный на\s+\\pi\s*\.",
        raw,
    )
    if match:
        return geometry("diameter_apex", match.groups(), "volume")
    match = re.fullmatch(
        r"Конус получается при вращении равнобедренного прямоугольного треугольника ABC вокруг катета, равного\s+(.+?)\s*\. Найдите его объем, деленный на\s+\\pi\s*\.",
        raw,
    )
    if match:
        return geometry("rotation", (match[1], "90"), "volume")
    return None


def read_question(html, source=None):
    from .cone_similarity import read as similarity

    raw = text(html, source)
    if re.fullmatch(
        r"Найдите объем V части конуса, изображенной на рисунке\. В ответе укажите\s+(?:\\frac\{V\}\{\\pi\}|V\\div\s*\\pi)\s*\.",
        raw,
    ):
        from .cone_cut import read

        return read(source)
    try:
        m = similarity(raw, source) or _special(raw)
        if m:
            return m
        for input_kind, pattern in SETUPS:
            for target, request in QUESTIONS:
                match = re.fullmatch(pattern + r"\s*" + request, raw)
                if match:
                    return geometry(input_kind, match.groups(), target)
    except UnsupportedCondition as exc:
        raise ContentPlanError(str(exc)) from exc
    raise ContentPlanError("one complete reviewed cone question is required")
