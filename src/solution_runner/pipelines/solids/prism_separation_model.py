"""Verify section normals in square and triangular prisms before computing distances."""

import re
from dataclasses import replace

import sympy as sp

from ..core.errors import ContentPlanError
from .measurements import positive
from .spatial_metric_model import model

MODES = {"square_prism_section_distance", "triangle_prism_section_distance"}
SQUARE = (
    r"[ВB] правильной четырехугольной призме ABCDA_1B_1C_1D_1 сторона AB основания равна (.+?), а боковое ребро AA_1 равно (.+?)\. "
    r"На ребрах BC и C_1D_1 отмечены точки K и L соответственно, причем (.+?)\. "
    r"Плоскость γ параллельна прямой BD и содержит точки K и L\. Докажите, что прямая (AC_1|A_1C) перпендикулярна плоскости γ\. "
    r"Найдите расстояние от точки (B_1|B) до плоскости γ\."
)
TRIANGLE = (
    r"[ВB] правильной треугольной призме ABCA_1B_1C_1 сторона основания равна (.+?), а боковое ребро AA_1 равно (.+?)\. "
    r"На ребрах AB и B_1C_1 отмечены точки K и L, соответственно, причем (.+?)\. "
    r"Точка M [—–-] середина ребра A_1C_1\. Плоскость γ параллельна ребру AC и содержит точки K и L\. "
    r"Докажите, что прямая BM перпендикулярна плоскости γ\. Найдите расстояние от точки C до плоскости γ\."
)


def _positions(raw, first, second):
    equal = re.fullmatch(first + r"\s*=\s*" + second + r"\s*=\s*(.+)", raw)
    if equal:
        value = positive(equal[1])
        return value, value
    separate = re.fullmatch(
        first + r"\s*=\s*(.+?), (?:а )?" + second + r"\s*=\s*(.+)", raw
    )
    if not separate:
        raise ContentPlanError("both section points need their exact edge positions")
    return positive(separate[1]), positive(separate[2])


def _solve(groups, triangular):
    a, h = map(positive, groups[:2])
    k, l = _positions(
        groups[2], "AK" if triangular else "BK", "B_1L" if triangular else "C_1L"
    )
    if not (k < a and l < a):
        raise ContentPlanError("section points must lie inside the stated edges")
    diagonal, target = ("BM", "C") if triangular else groups[3:]
    width = sp.sqrt(3) * a / 2 if triangular else sp.sqrt(2) * a
    expected = (
        3 * a * (a - k - l) / 4
        if triangular
        else a * ((k + l - a) if diagonal == "AC_1" else (a - k - l))
    )
    if sp.simplify(h * h - expected) != 0:
        raise ContentPlanError(
            "the requested diagonal is not normal to the section plane"
        )
    q = {
        "a": a,
        "H": h,
        "k": k,
        "l": l,
        "width": width,
        "normal_z": sp.simplify((a - k - l) / h),
    }
    if triangular:
        q.update(
            NE=k * width / a,
            MF=(a - l) * width / a,
            EP=(a - k - l) * width / a,
            normal_z=width * (a - k - l) / (a * h),
        )
        answer = q["NE"] / sp.sqrt(1 + q["normal_z"] ** 2)
    else:
        q.update(
            CE=(a - k) / sp.sqrt(2),
            C1F=l / sp.sqrt(2),
            AE=(a + k) / sp.sqrt(2),
            diagonal=sp.sqrt(width * width + h * h),
        )
        q.update(EF=sp.sqrt(h * h + (q["C1F"] - q["CE"]) ** 2))
        answer = (a - l if target == "B_1" else k) / sp.sqrt(2 + q["normal_z"] ** 2)
    m = model(
        "triangle_prism_section_distance"
        if triangular
        else "square_prism_section_distance",
        tuple(zip(("a", "H", "k", "l"), (a, h, k, l), strict=True)),
        q,
        (diagonal, target),
        answer,
    )
    return replace(m, squares=tuple(v * v for v in (a, h, k, l)))


def read(raw):
    raw = raw.replace(r"\gamma", "γ")
    for pattern, triangular in ((SQUARE, False), (TRIANGLE, True)):
        match = re.fullmatch(pattern, raw)
        if match:
            return _solve(match.groups(), triangular)
    return None
