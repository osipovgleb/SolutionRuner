"""Read actual cone similarity directions, section ratios and liquid fill fractions."""

import re

import sympy as sp

from ..core.errors import ContentPlanError
from .cone_model import ConeQuantity
from .measurements import positive


def _similar(kind, given, ratio):
    amount = given[0]
    if not 0 < ratio < 1:
        raise ContentPlanError(
            "the smaller cone height fraction must be between zero and one"
        )
    power = 3 if kind in {"volume", "liquid"} else 2
    answer = (
        amount * (ratio ** (-power) - 1) if kind == "liquid" else amount * ratio**power
    )
    return ConeQuantity("similarity", kind, given, sp.simplify(answer), ratio=ratio)


def _scale(raw):
    match = re.fullmatch(
        r"Во сколько раз (уменьшится|увеличится) (объем|площадь боковой поверхности) конуса, если (его высота|радиус (?:его )?основания|его образующая) (уменьшится|увеличится|уменьшить|увеличить) в\s+(.+?)\s+раза?, а (радиус основания|высота|образующая) останется прежн(?:им|ей)\?",
        raw,
    )
    if not match:
        return None
    request, measure, parameter, change, number, fixed = match.groups()
    kind = "volume" if measure == "объем" else "lateral"
    axis = (
        "height"
        if parameter == "его высота"
        else "slant"
        if parameter == "его образующая"
        else "radius"
    )
    expected = {
        ("volume", "height"): "радиус основания",
        ("volume", "radius"): "высота",
        ("lateral", "slant"): "радиус основания",
        ("lateral", "radius"): "образующая",
    }
    if expected.get((kind, axis)) != fixed or request.startswith(
        "уменьш"
    ) != change.startswith("уменьш"):
        raise ContentPlanError(
            "the requested cone scale and fixed dimension must agree"
        )
    factor = positive(number)
    if factor <= 1:
        raise ContentPlanError("a cone comparison factor must exceed one")
    ratio = 1 / factor if change.startswith("уменьш") else factor
    power = 2 if (kind, axis) == ("volume", "radius") else 1
    return ConeQuantity(
        "scale", kind, (factor,), sp.simplify(factor**power), axis, ratio=ratio
    )


def read(raw, source):
    m = _scale(raw)
    if m:
        return m
    match = re.fullmatch(
        r"Объем конуса равен\s+(.+?)\s*\. Через середину высоты параллельно основанию конуса проведено сечение, которое является основанием меньшего конуса с той же вершиной\. Найдите объем меньшего конуса\.",
        raw,
    )
    if match:
        return _similar("volume", (positive(match[1]),), sp.Rational(1, 2))
    match = re.fullmatch(
        r"Площадь полной поверхности конуса равна\s+(.+?)\s*\. Параллельно основанию конуса проведено сечение, делящее высоту в отношении\s+(.+?)\s*:\s*(.+?)\s*, считая от вершины конуса\. Найдите площадь полной поверхности отсеченного конуса\.",
        raw,
    )
    if match:
        amount, a, b = tuple(positive(s) for s in match.groups())
        return _similar("surface", (amount, a, b), a / (a + b))
    match = re.fullmatch(
        r"Площадь основания конуса равна\s+(.+?)\s*\. Плоскость, параллельная плоскости основания конуса, делит его высоту на отрезки длиной\s+(.+?)\s+и\s+(.+?)\s*, считая от вершины\. Найдите площадь сечения конуса этой плоскостью\.",
        raw,
    )
    if match:
        amount, a, b = tuple(positive(s) for s in match.groups())
        return _similar("section", (amount, a, b), a / (a + b))
    match = re.fullmatch(
        r"В сосуде, имеющем форму конуса, уровень жидкости достигает\s+(.+?)\s+высоты\. Объем жидкости равен\s+(.+?)\s+мл\. Сколько миллилитров жидкости нужно долить, чтобы (?:полностью наполнить сосуд|наполнить сосуд доверху)\?",
        raw,
    )
    if match:
        ratio, amount = (positive(s) for s in match.groups())
    else:
        match = re.fullmatch(
            r"В сосуд, имеющий форму конуса, налили\s+(.+?)\s+мл жидкости до половины высоты сосуда \(см\. рис\.\)\. Сколько миллилитров жидкости нужно долить в сосуд, чтобы заполнить его доверху\?",
            raw,
        )
        if not match:
            return None
        amount, ratio = positive(match[1]), sp.Rational(1, 2)
    from .cone_sources import LIQUID

    if source not in LIQUID:
        raise ContentPlanError("a reviewed vertex-down vessel diagram is required")
    return _similar("liquid", (amount,), ratio)
