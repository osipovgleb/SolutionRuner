"""Compute cylinder quantities from the actual dimensions, units and scale directions."""

import re
from dataclasses import dataclass

import sympy as sp

from ..core.errors import ContentPlanError
from ..probability.common import UnsupportedCondition
from . import cylinder_cut
from .cylinder_input import text
from .measurements import positive

PI_END = r"(, деленную на\s+\\pi)?\s*\."
VOLUME_UNIT = r"(см\^3|куб\.\s*см|литров|литра|литр|литрах|л)"
PATTERNS = (
    (
        "displacement",
        "",
        r"В цилиндрический сосуд налили\s+(.+?)\s+см\^3 воды\.\s*Уровень воды при этом достигает высоты\s+(.+?)\s+см\.\s*В жидкость полностью погрузили деталь\.\s*При этом уровень жидкости в сосуде поднялся на\s+(.+?)\s+см\.\s*Чему равен объем детали\?\s*Ответ выразите в\s+см\^3\s*\.",
    ),
    (
        "displacement",
        "factor",
        r"В цилиндрический сосуд налили\s+(.+?)\s+"
        + VOLUME_UNIT
        + r" воды\.\s*В воду полностью погрузили деталь\.\s*При этом уровень жидкости в сосуде увеличился в\s+(.+?)\s+раза?\.\s*Найдите объем детали\.\s*Ответ выразите в\s+"
        + VOLUME_UNIT
        + r"\s*\.",
    ),
    (
        "displacement",
        "factor",
        r"В цилиндрический сосуд, в котором находится\s+(.+?)\s+"
        + VOLUME_UNIT
        + r" воды, опущена деталь\.\s*При этом уровень жидкости в сосуде поднялся в\s+(.+?)\s+раза?\.\s*Чему равен объем детали\?\s*Ответ выразите в\s+"
        + VOLUME_UNIT
        + r"\s*\.",
    ),
    (
        "transfer",
        "",
        r"В цилиндрическом сосуде уровень жидкости достигает\s+(.+?)\s+см\.\s*На какой высоте будет находиться уровень жидкости, если ее перелить во второй сосуд, диаметр которого в\s+(.+?)\s+раза? (больше|меньше) первого\?\s*Ответ (?:дайте|выразите) в сантиметрах\s*\.",
    ),
    (
        "volume_ratio",
        "",
        r"Объем первого цилиндра равен\s+(.+?)\s+м\^3\.\s*У второго цилиндра высота в\s+(.+?)\s+раза? (больше|меньше), а радиус основания\s*[—–-]?\s*в\s+(.+?)\s+раза? (больше|меньше), чем у первого\.\s*Найди(?:те)? объем второго цилиндра(?:\.\s*Ответ дайте в кубических метрах|\s*\(в м\^3\))\s*\.",
    ),
    (
        "lateral",
        "radius",
        r"Радиус основания цилиндра равен\s+(.+?)\s*,\s*высота равна\s+(.+?)\s*\.\s*Найдите площадь боковой поверхности цилиндра"
        + PI_END,
    ),
    (
        "lateral",
        "circumference",
        r"Длина окружности основания цилиндра равна\s+(.+?)\s*,\s*высота равна\s+(.+?)\s*\.\s*Найдите площадь боковой поверхности цилиндра\s*\.",
    ),
    (
        "height",
        "circumference",
        r"Длина окружности основания цилиндра равна\s+(.+?)\s*\.\s*Площадь боковой поверхности равна\s+(.+?)\s*\.\s*Найдите высоту цилиндра\s*\.",
    ),
    (
        "height",
        "diameter",
        r"Площадь боковой поверхности цилиндра равна\s+(.+?)\s*,\s*а диаметр основания\s*(?:равен|[—–-])\s*(.+?)\s*\.\s*Найдите высоту цилиндра\s*\.",
    ),
    (
        "diameter",
        "",
        r"Площадь боковой поверхности цилиндра равна\s+(.+?)\s*,\s*а высота\s*(?:равна|[—–-])\s*(.+?)\s*\.\s*Найдите диаметр основания\s*\.",
    ),
    (
        "axial_lateral",
        "",
        r"Площадь осевого сечения цилиндра равна\s+(.+?)\s*\.\s*Найдите площадь боковой поверхности цилиндра"
        + PI_END,
    ),
)


@dataclass(frozen=True)
class CylinderQuantity:
    mode: str
    given: tuple[sp.Expr, ...]
    answer: sp.Expr
    kind: str = ""
    divide_pi: bool = False
    unit: str = ""


def _scale(raw, direction):
    factor = positive(raw, words=True)
    if (factor - 1).is_positive is not True:
        raise ContentPlanError("a cylinder comparison factor must exceed one")
    return factor if direction == "больше" else 1 / factor


def _solve(mode, kind, groups):
    if mode == "displacement" and kind == "factor":
        volume, first, raw_factor, last = groups
        unit = "л" if first.startswith("л") else "см^3"
        if unit != ("л" if last.startswith("л") else "см^3"):
            raise ContentPlanError(
                "the displaced volume must use the requested input unit"
            )
        v, factor = positive(volume), _scale(raw_factor, "больше")
        return CylinderQuantity(
            mode, (v, factor), sp.simplify(v * (factor - 1)), kind, unit=unit
        )
    if mode == "displacement":
        v, h, delta = tuple(positive(s) for s in groups)
        return CylinderQuantity(
            mode, (v, h, delta), sp.simplify(v * delta / h), unit="см^3"
        )
    if mode == "transfer":
        h = positive(groups[0])
        ratio = _scale(*groups[1:])
        return CylinderQuantity(mode, (h, ratio), sp.simplify(h / ratio**2), unit="см")
    if mode == "volume_ratio":
        v = positive(groups[0])
        height = _scale(*groups[1:3])
        radius = _scale(*groups[3:5])
        return CylinderQuantity(
            mode, (v, height, radius), sp.simplify(v * height * radius**2), unit="м^3"
        )
    divided = mode == "axial_lateral" or mode == "lateral" and kind == "radius"
    divide_pi = bool(groups[-1]) if divided else False
    given = (
        tuple(positive(s, pi=True) for s in groups[:-1] if s is not None)
        if divided
        else tuple(positive(s, pi=True) for s in groups)
    )
    if mode == "lateral":
        first, h = given
        surface = 2 * sp.pi * first * h if kind == "radius" else first * h
        answer = surface / (sp.pi if divide_pi else 1)
    elif mode == "height":
        circumference, surface = (
            given if kind == "circumference" else (sp.pi * given[1], given[0])
        )
        answer = surface / circumference
    elif mode == "diameter":
        answer = given[0] / (sp.pi * given[1])
    else:
        answer = given[0] * (1 if divide_pi else sp.pi)
    return CylinderQuantity(mode, given, sp.simplify(answer), kind, divide_pi)


def read_question(html, source=None):
    raw = text(html, source)
    if re.fullmatch(
        r"Найдите объем V части цилиндра, изображенной на рисунке\. В ответе укажите\s+(?:\\frac\{V\}\{\\pi\}|V\\div\s*\\pi)\s*\.",
        raw,
    ):
        return cylinder_cut.read(source)
    try:
        for mode, kind, pattern in PATTERNS:
            match = re.fullmatch(pattern, raw)
            if match:
                return _solve(mode, kind, match.groups())
    except UnsupportedCondition as exc:
        raise ContentPlanError(str(exc)) from exc
    raise ContentPlanError("one complete reviewed cylinder question is required")
