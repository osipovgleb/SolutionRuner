"""Linear angles and the cosine law retain the geometric parent method."""

import sympy as sp

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value
from . import cube_projection_claims
from .spatial_distance_proofs import parts


def _center(m):
    q = m.q
    return (
        "<p>Пусть O — центр куба, M — середина A₁B. В треугольнике BA₁D₁ отрезок MO — средняя линия, поэтому MO ∥ A₁D₁ и MO ⟂ A₁B. Треугольник BA₁C₁ равносторонний, следовательно, его медиана C₁M также перпендикулярна A₁B. Угол OMC₁ — линейный угол между плоскостями. Обозначим ребро куба через a &gt; 0:</p>"
        + line(r"OM=\frac{A_1D_1}{2}=\frac{a}{2}")
        + line(
            r"MC_1=\frac{A_1C_1\sqrt3}{2}=\frac{a\sqrt2\sqrt3}{2}=" + value(q["second"])
        )
        + line(r"OC_1=\frac{AC_1}{2}=\frac{a\sqrt3}{2}")
        + "<p>По теореме косинусов в треугольнике OMC₁:</p>"
        + line(r"\cos\angle OMC_1=\frac{OM^2+MC_1^2-OC_1^2}{2OM\cdot MC_1}")
        + line(
            r"\cos\angle OMC_1=\frac{"
            + bracket(q["first"])
            + "^2+"
            + bracket(q["second"])
            + "^2-"
            + bracket(q["opposite"])
            + r"^2}{2\cdot "
            + bracket(q["first"])
            + r"\cdot "
            + bracket(q["second"])
            + "}="
            + value(q["cosine"])
        )
    )


def _altitudes(m):
    q = m.q
    return (
        "<p>Пусть M — середина AD₁. Треугольники AB₁D₁ и ACD₁ равносторонние: каждая их сторона — диагональ грани куба. Поэтому медианы B₁M и CM перпендикулярны общей стороне AD₁. Угол B₁MC — линейный угол искомого двугранного угла. Обозначим ребро куба через a &gt; 0:</p>"
        + line(r"AB_1=AD_1=AC=B_1C=a\sqrt2")
        + line(r"B_1M=CM=\sqrt{AB_1^2-\left(\frac{AD_1}{2}\right)^2}")
        + line(r"B_1M=CM=\sqrt{2a^2-\frac{a^2}{2}}=" + value(q["first"]))
        + "<p>По теореме косинусов в треугольнике B₁MC:</p>"
        + line(r"\cos\angle B_1MC=\frac{B_1M^2+CM^2-B_1C^2}{2B_1M\cdot CM}")
        + line(
            r"\cos\angle B_1MC=\frac{"
            + bracket(q["first"])
            + "^2+"
            + bracket(q["second"])
            + "^2-"
            + bracket(q["opposite"])
            + r"^2}{2\cdot "
            + bracket(q["first"])
            + r"\cdot "
            + bracket(q["second"])
            + "}="
            + value(q["cosine"])
        )
    )


def _rectangle(m, pictures):
    q = m.q
    t = sp.simplify(q["face_diagonal"] / (2 * q["a"]))
    result = (
        pictures["image_2"]
        + "<p><b>Другой способ.</b> Примем ребро куба за единицу. В прямоугольнике CDA₁B₁ точка M — середина DA₁; она совпадает с серединой AD₁. Проведём MK ∥ CD. По симметрии относительно MK угол B₁MC вдвое больше угла KMC:</p>"
        + line(r"MD=\frac{DA_1}{2}=" + value(t) + r",\qquad DC=1")
        + line(r"\tan\angle MCD=\frac{MD}{DC}=" + value(t))
        + line(r"\angle B_1MC=2\angle KMC=2\angle MCD=2\arctan " + bracket(t))
    )
    if m.names[2] == "cosine":
        result += line(
            r"\cos\angle B_1MC=\frac{1-"
            + bracket(t)
            + "^2}{1+"
            + bracket(t)
            + "^2}="
            + value(q["cosine"])
        )
    return result


def render(m, pictures):
    first = cube_projection_claims.render(m)
    second = _center(m) if m.names[0] == "center" else _altitudes(m)
    result = parts(pictures.get("image_1", "") + first, second)
    if "image_2" in pictures:
        result += _rectangle(m, pictures)
    return result
