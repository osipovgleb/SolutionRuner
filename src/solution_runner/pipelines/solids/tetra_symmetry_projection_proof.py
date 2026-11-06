"""Use the parent's two Pythagorean equations for the perpendicular foot."""

import sympy as sp

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value
from .spatial_distance_proofs import parts


def _claim():
    return "<p>Треугольники SBC и ABC равнобедренные и имеют общее основание BC. Проведём медианы SN и AN к этому основанию. Точка N — середина BC, поэтому обе медианы являются высотами. Прямая BC перпендикулярна двум пересекающимся прямым SN и AN, а значит, и плоскости ASN. В частности, BC перпендикулярна SA, что и требовалось доказать.</p>"


def _medians(m):
    q = m.q
    return (
        line(r"BN=NC=\frac{BC}{2}=" + value(q["w"] / 2))
        + line(
            r"SN=\sqrt{SB^2-BN^2}=\sqrt{"
            + bracket(q["u"])
            + "^2-"
            + bracket(q["w"] / 2)
            + "^2}="
            + value(q["SN"])
        )
        + line(
            r"AN=\sqrt{AB^2-BN^2}=\sqrt{"
            + bracket(q["v"])
            + "^2-"
            + bracket(q["w"] / 2)
            + "^2}="
            + value(q["AN"])
        )
    )


def _calculation(m):
    q = m.q
    inside = 0 < q["foot"] < 1
    introduction = "<p>Построим высоту AM треугольника ASN. Она перпендикулярна SN и направлению BC, поэтому AM ⟂ SBC. Отрезок SM — проекция SA на плоскость SBC.</p>"
    unknown = (
        "<p>Положим SM = x, тогда MN = SN − x. Выразим квадрат AM из прямоугольных треугольников AMS и AMN и приравняем полученные значения:</p>"
        if inside
        else "<p>Обозначим через x направленную координату M на прямой SN с началом в S и положительным направлением к N. Тогда SM = |x|, MN = |SN − x|. Выразим квадрат AM из прямоугольных треугольников AMS и AMN:</p>"
    )
    coefficient = 2 * q["SN"]
    right = sp.simplify(q["w"] ** 2 + q["SN"] ** 2 - q["AN"] ** 2)
    return (
        introduction
        + "<p>Найдём длины медиан по теореме Пифагора:</p>"
        + _medians(m)
        + unknown
        + line(r"AM^2=SA^2-SM^2=AN^2-MN^2")
        + line(
            bracket(q["w"])
            + "^2-x^2="
            + bracket(q["AN"])
            + "^2-"
            + r"\left("
            + value(q["SN"])
            + r"-x\right)^2"
        )
        + line(value(coefficient) + "x=" + value(right))
        + line("x=" + value(q["x"]))
        + (
            "<p>Искомый угол α найдём в прямоугольном треугольнике ASM:</p>"
            if q["SM"] != 0
            else "<p>Точка M совпадает с S: проекция SA — точка, поэтому искомый угол α прямой. Длина проекции равна нулю:</p>"
        )
        + line(
            r"\cos\alpha=\frac{SM}{SA}=\frac{"
            + bracket(q["SM"])
            + "}{"
            + bracket(q["w"])
            + "}="
            + value(q["cosine"])
        )
    )


def render(m, pictures):
    picture = pictures.get("image_1", pictures.get("box_distance_solution", ""))
    return parts(picture + _claim(), _calculation(m))
