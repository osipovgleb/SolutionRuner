"""The parent's parallelogram proof, side lengths and diagonal-area calculation."""

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value
from .spatial_distance_proofs import parts


def _names(m):
    if m.names[0] == "W":
        return "CTA_1W", "CT", "CW", "CA_1", "WT", "DW", "D_1W"
    return "AOC_1P", "AO", "OC_1", "AC_1", "OP", "BO", "B_1O"


def _construction(m, pictures):
    q = m.q
    _boundary, s1, s2, _d1, _d2, low, high = _names(m)
    text = (
        "<p>Пусть плоскость CA₁W пересекает BB₁ в T. Противоположные грани параллельны, поэтому CT ∥ A₁W и A₁T ∥ CW. Сечение CTA₁W — параллелограмм.</p>"
        if m.names[0] == "W"
        else "<p>Пусть плоскость AOC₁ пересекает DD₁ в P. Противоположные грани параллельны, поэтому AP ∥ C₁O и C₁P ∥ AO. Сечение AOC₁P — параллелограмм.</p>"
    )
    text += line(
        low
        + r"=\frac{"
        + value(dict(m.given)["p"])
        + "}{"
        + value(dict(m.given)["p"] + dict(m.given)["q"])
        + r"}\cdot AA_1="
        + value(q["low"])
    )
    text += line(
        high
        + r"=AA_1-"
        + low
        + "="
        + value(q["height"])
        + "-"
        + bracket(q["low"])
        + "="
        + value(q["high"])
    )
    # CT uses AD and the upper remainder; CW uses AB and the lower remainder.
    first, second = (
        (q["side2"], q["side1"]) if m.names[0] == "W" else (q["side1"], q["side2"])
    )
    x, y = (q["b"], q["a"]) if m.names[0] == "W" else (q["a"], q["b"])
    z, w = (q["high"], q["low"]) if m.names[0] == "W" else (q["low"], q["high"])
    text += (
        "<p>В прямоугольных треугольниках соответствующих боковых граней применим теорему Пифагора:</p>"
        + line(
            s1 + r"=\sqrt{" + bracket(x) + "^2+" + bracket(z) + "^2}=" + value(first)
        )
        + line(
            s2 + r"=\sqrt{" + bracket(y) + "^2+" + bracket(w) + "^2}=" + value(second)
        )
    )
    text += (
        "<p>Смежные стороны параллелограмма равны, поэтому он является ромбом.</p>"
        if q["rhombus"]
        else "<p>Получен параллелограмм с различными смежными сторонами. Угол между его диагоналями найдём по теореме косинусов.</p>"
    )
    return pictures.get("image_1", "") + text


def _quantity(m, pictures):
    q = m.q
    _boundary, _s1, _s2, d1, _d2, _low, _high = _names(m)
    result = (
        "<p>Найдём диагональ сечения, которая одновременно является диагональю параллелепипеда:</p>"
        + pictures.get("image_2", "")
        + line(
            d1
            + r"=\sqrt{AB^2+AD^2+AA_1^2}=\sqrt{"
            + bracket(q["a"])
            + "^2+"
            + bracket(q["b"])
            + "^2+"
            + bracket(q["height"])
            + "^2}="
            + value(q["diagonal"])
        )
    )
    return result + (_rhombus_area(m) if q["rhombus"] else _general_area(m))


def _rhombus_area(m):
    q = m.q
    boundary, s1, _s2, d1, d2, _low, _high = _names(m)
    first = q["side2"] if m.names[0] == "W" else q["side1"]
    return (
        "<p>Диагонали ромба перпендикулярны и делятся точкой пересечения пополам. По теореме Пифагора:</p>"
        + line(d2 + r"=2\sqrt{" + s1 + r"^2-\left(\frac{" + d1 + r"}{2}\right)^2}")
        + line(
            d2
            + r"=\sqrt{4\cdot "
            + bracket(first)
            + "^2-"
            + bracket(q["diagonal"])
            + "^2}="
            + value(q["other"])
        )
        + line("S_{" + boundary + r"}=\frac{" + d1 + r"\cdot " + d2 + "}{2}")
        + line(
            "S_{"
            + boundary
            + r"}=\frac{"
            + bracket(q["diagonal"])
            + r"\cdot "
            + bracket(q["other"])
            + "}{2}="
            + value(m.answer)
        )
    )


def _general_area(m):
    q = m.q
    boundary, s1, s2, d1, d2, low, high = _names(m)
    delta = -q["dot"]
    difference = s2 + "^2-" + s1 + "^2" if m.names[0] == "O" else s1 + "^2-" + s2 + "^2"
    return (
        "<p>Вторая диагональ соединяет точки на противоположных боковых рёбрах. Найдём её по теореме Пифагора. Для угла φ между направленными диагоналями теорема косинусов в треугольниках при их пересечении даёт:</p>"
        + line(
            d2 + r"=\sqrt{AB^2+AD^2+(" + high + "-" + low + r")^2}=" + value(q["other"])
        )
        + line(
            r"\cos\varphi=\frac{"
            + difference
            + "}{"
            + d1
            + r"\cdot "
            + d2
            + r"}=\frac{"
            + value(delta)
            + "}{"
            + bracket(q["diagonal"])
            + r"\cdot "
            + bracket(q["other"])
            + "}"
        )
        + line(
            "S_{"
            + boundary
            + r"}=\frac12\sqrt{"
            + d1
            + "^2"
            + d2
            + "^2-("
            + s1
            + "^2-"
            + s2
            + r"^2)^2}="
            + value(m.answer)
        )
    )


def render(m, pictures):
    return parts(_construction(m, pictures), _quantity(m, pictures))
