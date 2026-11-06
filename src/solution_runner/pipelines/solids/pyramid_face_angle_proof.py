"""Opposite-edge perpendicularity, face area and the parent's cosine law."""

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value
from .spatial_distance_proofs import parts


def _perpendicular():
    return "<p>Пусть SABC — данная пирамида, SH — её высота, M — середина BC. Проекция прямой AS на основание — прямая AH, совпадающая с медианой AM равностороннего треугольника ABC. Поэтому AM ⟂ BC. По теореме о трёх перпендикулярах AS ⟂ BC. Аналогично BS ⟂ AC и CS ⟂ AB.</p>"


def _lengths(m):
    q = m.q
    return (
        (
            "<p>Угол SMH — угол между боковой гранью и основанием. Пусть a &gt; 0 — произвольный масштаб длины. Выберем апофему:</p>"
            if m.names[0] == "scaled"
            else "<p>Угол SMH — угол между боковой гранью и основанием. По условию:</p>"
        )
        + line("SM=" + value(q["apothem"]))
        + "<p>Центр H делит медиану AM в отношении 2 : 1, считая от вершины A. Вычислим необходимые длины:</p>"
        + line(
            r"MH=SM\cos\angle SMH="
            + bracket(q["apothem"])
            + r"\cdot "
            + bracket(q["rho"])
            + "="
            + value(q["MH"])
        )
        + line(r"AM=3MH=3\cdot " + bracket(q["MH"]) + "=" + value(q["AM"]))
        + line(
            r"BC=\frac{2AM}{\sqrt3}=\frac{2\cdot "
            + bracket(q["AM"])
            + r"}{\sqrt3}="
            + value(q["a"])
        )
        + line(
            r"SB=\sqrt{BM^2+SM^2}=\sqrt{\left(\frac{"
            + value(q["a"])
            + r"}{2}\right)^2+"
            + bracket(q["apothem"])
            + "^2}="
            + value(q["e"])
        )
    )


def _altitudes(m):
    q = m.q
    return (
        "<p>Пусть CK — высота треугольника BSC, проведённая к SB. Треугольники BSC и BSA равны по трём сторонам, поэтому основание высоты из A на SB — та же точка K. Следовательно, CK ⟂ SB и AK ⟂ SB, а угол AKC — линейный угол между боковыми гранями.</p>"
        + "<p>Вычислим площадь грани BSC двумя способами:</p>"
        + line(r"S_{BSC}=\frac{1}{2}SM\cdot BC=\frac{1}{2}CK\cdot SB")
        + line(
            r"CK=\frac{SM\cdot BC}{SB}=\frac{"
            + bracket(q["apothem"])
            + r"\cdot "
            + bracket(q["a"])
            + "}{"
            + bracket(q["e"])
            + "}="
            + value(q["CK"])
        )
        + "<p>Треугольник AKC равнобедренный. По теореме косинусов:</p>"
        + line(
            r"\cos\angle AKC=\frac{AK^2+CK^2-AC^2}{2AK\cdot CK}=\frac{2CK^2-AC^2}{2CK^2}"
        )
        + line(
            r"\cos\angle AKC=\frac{2\cdot "
            + bracket(q["CK"])
            + "^2-"
            + bracket(q["a"])
            + r"^2}{2\cdot "
            + bracket(q["CK"])
            + "^2}="
            + value(q["cosine"])
        )
    )


def render(m, pictures):
    return parts(
        pictures.get("image_1", "") + _perpendicular(), _lengths(m) + _altitudes(m)
    )
