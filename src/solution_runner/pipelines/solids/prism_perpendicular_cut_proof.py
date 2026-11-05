"""Perpendicular-face construction precedes every direct or inverse calculation."""

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value
from .spatial_distance_proofs import parts


def _proof(m):
    intro = "<p>Обозначим середину A₁B₁ через K. В правильном треугольнике A₁B₁C₁ медиана C₁K является высотой, поэтому C₁K ⟂ A₁B₁. Прямая C₁K также перпендикулярна направлению боковых рёбер прямой призмы, а значит, перпендикулярна грани ABB₁A₁.</p>"
    if m.mode.endswith("height"):
        return (
            intro
            + "<p>Плоскость α перпендикулярна грани ABB₁A₁ и содержит C₁. Поэтому перпендикуляр C₁K к этой грани лежит в α. Следовательно, K принадлежит плоскости сечения: ребро A₁B₁ действительно делится пополам.</p>"
        )
    return (
        intro
        + "<p>Плоскость MKC₁ содержит перпендикуляр C₁K к грани ABB₁A₁. Следовательно, она перпендикулярна этой грани и совпадает с проведённой через MK плоскостью α. Поэтому C₁ принадлежит α.</p>"
    )


def _ratio(m):
    coefficient = dict(m.given)["coefficient"]
    denominator = coefficient + 1
    if m.names[1] == "AM":
        return line(r"AA_1=AM+A_1M=" + value(denominator) + r"A_1M") + line(
            r"A_1M=\frac{AA_1}{" + value(denominator) + "}"
        )
    return line(r"AA_1=AM+A_1M=" + value(denominator) + r"AM") + line(
        r"A_1M=\frac{" + value(coefficient) + "}{" + value(denominator) + r"}AA_1"
    )


def _area(m):
    q = m.q
    return (
        "<p>Сечение — треугольник MKC₁. Из данного отношения на AA₁ получаем:</p>"
        + _ratio(m)
        + line(r"A_1M=" + value(q["top"]) + r"\cdot AA_1=" + value(q["A1M"]))
        + line(
            r"A_1K=\frac{A_1B_1}{2}=\frac{" + value(q["a"]) + "}{2}=" + value(q["A1K"])
        )
        + "<p>В прямоугольном треугольнике MA₁K по теореме Пифагора:</p>"
        + line(
            r"MK=\sqrt{A_1M^2+A_1K^2}=\sqrt{"
            + bracket(q["A1M"])
            + "^2+"
            + bracket(q["A1K"])
            + "^2}="
            + value(q["MK"])
        )
        + line(
            r"KC_1=\frac{\sqrt3}{2}A_1B_1=\frac{\sqrt3}{2}\cdot "
            + bracket(q["a"])
            + "="
            + value(q["KC1"])
        )
        + "<p>Поскольку KC₁ перпендикулярен грани ABB₁A₁, он перпендикулярен и MK. Треугольник MKC₁ прямоугольный:</p>"
        + line(
            r"S_{MKC_1}=\frac{KC_1\cdot MK}{2}=\frac{"
            + bracket(q["KC1"])
            + r"\cdot "
            + bracket(q["MK"])
            + "}{2}="
            + value(m.answer)
        )
    )


def _inverse(m):
    q = m.q
    return (
        "<p>Обозначим общее ребро призмы через u &gt; 0. Тогда высота также равна u. По условию:</p>"
        + _ratio(m)
        + line(r"A_1M=" + value(q["top"]) + r"u,\qquad A_1K=\frac{u}{2}")
        + line(r"MK=\sqrt{A_1M^2+A_1K^2}=u\sqrt{" + bracket(q["top"]) + r"^2+\frac14}")
        + line(r"KC_1=\frac{\sqrt3}{2}u")
        + "<p>Отрезок KC₁ перпендикулярен MK, поэтому по формуле площади прямоугольного треугольника:</p>"
        + line(
            r"S_{MKC_1}=\frac{KC_1\cdot MK}{2}=\frac{\sqrt3}{4}u^2\sqrt{"
            + bracket(q["top"])
            + r"^2+\frac14}"
        )
        + line(
            r"u^2=\frac{4\cdot "
            + bracket(q["area"])
            + r"}{\sqrt3\sqrt{"
            + bracket(q["top"])
            + r"^2+\frac14}}="
            + value(q["a"] ** 2)
        )
        + line(r"AA_1=u=" + value(m.answer))
    )


def render(m, pictures):
    from .prism_perpendicular_coordinates import render as coordinates

    return parts(
        pictures.get("image_1", "") + _proof(m),
        _inverse(m) if m.mode.endswith("height") else _area(m),
    ) + coordinates(m, pictures)
