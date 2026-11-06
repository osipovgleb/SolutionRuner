"""Retain the middle line and three cosine-law calculations from the parent."""

import sympy as sp

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value
from .spatial_distance_proofs import parts


def _claim(m):
    common = "<p>Пусть N — середина AC. Отрезок MN — средняя линия треугольника SCA, поэтому MN ∥ SA. Угол между прямыми BM и SA равен меньшему углу между прямыми BM и MN.</p>"
    if m.names[0] == "angle":
        return (
            common
            + "<p>Если угол BMN острый или прямой, он и есть искомый; если тупой — искомый угол дополняет BMN до 180°. Утверждение доказано.</p>"
        )
    first, second, projected = (
        ("SA", "BC", "AH") if m.names[0] == "SA_BC" else ("SB", "AC", "BH")
    )
    return (
        "<p>Проекция вершины S на основание — центр H равностороннего треугольника ABC. Прямая "
        + projected
        + " содержит высоту основания и потому перпендикулярна "
        + second
        + ". По теореме о трёх перпендикулярах "
        + first
        + " ⟂ "
        + second
        + ", что и требовалось доказать.</p>"
        + common
    )


def _lengths(m, picture):
    q = m.q
    half, e, cosine = value(q["MN"]), value(q["e"]), sp.latex(q["face_cosine"])
    return (
        "<p>Найдём стороны треугольника BMN. По теореме о средней линии:</p>"
        + line(r"MN=\frac{SA}{2}=" + half)
        + "<p>Боковые грани правильной пирамиды равны, M лежит на SC, поэтому косинус угла BSM равен данному косинусу ASB. По теореме косинусов:</p>"
        + line(r"BM=\sqrt{BS^2+SM^2-2BS\cdot SM\cos\angle BSM}")
        + line(
            r"BM=\sqrt{"
            + bracket(q["e"])
            + "^2+"
            + bracket(q["MN"])
            + r"^2-2\cdot "
            + e
            + r"\cdot "
            + half
            + r"\cdot "
            + r"\left("
            + cosine
            + r"\right)"
            + "}="
            + value(q["BM"])
        )
        + picture
        + "<p>Чтобы найти BN, сначала вычислим сторону основания по теореме косинусов в треугольнике BSC:</p>"
        + line(r"BC=\sqrt{BS^2+SC^2-2BS\cdot SC\cos\angle BSC}")
        + line(
            r"BC=\sqrt{2\cdot "
            + bracket(q["e"])
            + r"^2\left(1-"
            + cosine
            + r"\right)}="
            + value(q["a"])
        )
        + "<p>BN — высота равностороннего треугольника ABC:</p>"
        + line(
            r"BN=\frac{BC\sqrt3}{2}=\frac{"
            + bracket(q["a"])
            + r"\sqrt3}{2}="
            + value(q["BN"])
        )
    )


def _cosine(m):
    q = m.q
    conclusion = (
        "<p>Полученный косинус положителен, поэтому угол BMN острый и является искомым.</p>"
        if q["signed_cosine"] > 0
        else "<p>Если косинус отрицателен, угол BMN тупой, и меньший угол между прямыми дополняет его до 180°. При нулевом косинусе угол прямой. Поэтому для искомого косинуса берём модуль:</p>"
    )
    return (
        "<p>По теореме косинусов в треугольнике BMN:</p>"
        + line(r"\cos\angle BMN=\frac{BM^2+MN^2-BN^2}{2BM\cdot MN}")
        + line(
            r"\cos\angle BMN=\frac{"
            + bracket(q["BM"])
            + "^2+"
            + bracket(q["MN"])
            + "^2-"
            + bracket(q["BN"])
            + r"^2}{2\cdot "
            + bracket(q["BM"])
            + r"\cdot "
            + bracket(q["MN"])
            + "}="
            + value(q["signed_cosine"])
        )
        + conclusion
        + line(r"\cos\alpha=|\cos\angle BMN|=" + value(m.answer))
    )


def render(m, pictures):
    return parts(
        pictures.get("image_1", "") + _claim(m),
        _lengths(m, pictures.get("image_2", "")) + _cosine(m),
    )
