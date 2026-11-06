"""Necessary proof variants share the parent's section and three-perpendiculars method."""

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value
from .spatial_distance_proofs import parts


def _claim(m):
    q = m.q
    if m.names[0] == "length":
        return (
            "<p>В ромбе AB = AD, а угол BAD равен 60°, поэтому треугольник ABD равносторонний и BD = AD. По теореме Пифагора в боковых прямоугольных треугольниках:</p>"
            + line(
                r"AD_1^2=AD^2+DD_1^2="
                + bracket(q["a"])
                + "^2+"
                + bracket(q["height"])
                + "^2="
                + value(q["diagonal"] ** 2)
            )
            + line(
                r"DB_1^2=BD^2+BB_1^2="
                + bracket(q["a"])
                + "^2+"
                + bracket(q["height"])
                + "^2="
                + value(q["diagonal"] ** 2)
            )
            + "<p>Следовательно, AD₁ = DB₁.</p>"
        )
    if m.names[0] == "line_angles":
        return (
            "<p>В прямой призме боковые грани — прямоугольники. По теореме Пифагора:</p>"
            + line(
                r"CD_1=CB_1=\sqrt{"
                + bracket(q["a"])
                + "^2+"
                + bracket(q["height"])
                + "^2}="
                + value(q["diagonal"])
            )
            + "<p>Кроме того, A₁B₁ = A₁D₁ как стороны ромба, а A₁C — общая сторона. Треугольники A₁B₁C и A₁D₁C равны по трём сторонам, поэтому углы B₁A₁C и D₁A₁C равны. Так как AB ∥ A₁B₁ и AD ∥ A₁D₁, прямая A₁C образует равные углы с AB и AD.</p>"
        )
    return (
        "<p>Площадь боковой поверхности прямой призмы равна произведению периметра основания и высоты. Площадь основания-ромба равна произведению двух сторон и синуса угла между ними:</p>"
        + line(
            r"S_{\mathrm{бп}}=4aH=4\cdot "
            + bracket(q["a"])
            + r"\cdot "
            + bracket(q["height"])
            + "="
            + value(q["lateral"])
        )
        + line(
            r"S_{\mathrm{осн}}=a^2\sin\alpha="
            + bracket(q["a"])
            + r"^2\cdot "
            + bracket(q["sine"])
            + "="
            + value(q["base_area"])
        )
        + line(
            r"S_{\mathrm{пп}}=S_{\mathrm{бп}}+2S_{\mathrm{осн}}="
            + value(q["lateral"])
            + r"+2\cdot "
            + bracket(q["base_area"])
            + "="
            + value(q["total"])
        )
        + "<p>Все длины положительны. Проверим, что высота больше высоты ромба:</p>"
        + line(
            r"H^2-(a\sin\alpha)^2="
            + bracket(q["height"])
            + "^2-("
            + bracket(q["a"])
            + r"\cdot "
            + bracket(q["sine"])
            + ")^2="
            + value(q["margin_squared"])
            + r">0"
        )
        + "<p>Значит, H &gt; a sin α. Поэтому:</p>"
        + line(r"3S_{\mathrm{бп}}-2S_{\mathrm{пп}}=4a(H-a\sin\alpha)>0")
        + line(r"\frac{S_{\mathrm{бп}}}{S_{\mathrm{пп}}}>\frac{2}{3}")
    )


def render(m, pictures):
    q = m.q
    second = (
        "<p>Сечение плоскостью AC₁B — параллелограмм ABC₁D₁. Опустим из D перпендикуляр DH на AB. По теореме о трёх перпендикулярах D₁H также перпендикулярна AB. Следовательно, угол DHD₁ — линейный угол между плоскостью сечения и основанием.</p>"
        + line(
            r"DH=AD\sin\alpha="
            + bracket(q["a"])
            + r"\cdot\sin "
            + value(q["theta"])
            + r"^\circ="
            + value(q["DH"])
        )
        + "<p>В прямоугольном треугольнике DD₁H:</p>"
        + line(
            r"\tan\angle DHD_1=\frac{DD_1}{DH}=\frac{"
            + bracket(q["height"])
            + "}{"
            + bracket(q["DH"])
            + "}="
            + value(q["tan"])
        )
    )
    return parts(
        pictures.get("image_1", "")
        + "<p>Обозначим сторону основания через a, высоту призмы через H, острый угол ромба через α.</p>"
        + _claim(m),
        second,
    )
