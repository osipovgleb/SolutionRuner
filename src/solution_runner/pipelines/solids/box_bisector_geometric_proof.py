"""Keep the parent's third method: two perpendiculars and similar triangles."""

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value


def _calculation(m, pictures):
    q = m.q
    return (
        "<p>Чтобы найти след сечения на верхнем основании, в прямоугольнике AA₁C₁C проведём через M прямую MK ⟂ AC₁ до пересечения с A₁C₁. В верхнем основании проведём KT ⟂ A₁C₁ до пересечения с A₁B₁. По теореме, обратной теореме о трёх перпендикулярах, KT ⟂ AC₁. Поэтому плоскость MKT совпадает с α.</p>"
        + pictures.get("image_4", "")
        + "<p>Прямоугольные треугольники KMC₁ и AA₁C₁ подобны по общему углу при C₁:</p>"
        + line(r"A_1C_1=\sqrt{AB^2+BC^2}=" + value(q["top_diagonal"]))
        + line(r"AC_1=\sqrt{AB^2+BC^2+AA_1^2}=" + value(q["space_diagonal"]))
        + line(
            r"C_1K=\frac{C_1M\cdot AC_1}{A_1C_1}=\frac{AC_1^2}{2A_1C_1}=\frac{"
            + value(q["space_diagonal"] ** 2)
            + r"}{2\cdot "
            + bracket(q["top_diagonal"])
            + "}="
            + value(q["C1K"])
        )
        + line(
            r"A_1K=A_1C_1-C_1K="
            + value(q["top_diagonal"])
            + "-"
            + bracket(q["C1K"])
            + "="
            + value(q["A1K"])
        )
        + "<p>Теперь используем подобие прямоугольных треугольников TKA₁ и C₁B₁A₁:</p>"
        + line(r"\frac{TA_1}{A_1C_1}=\frac{A_1K}{A_1B_1}")
        + line(
            r"TA_1=\frac{A_1K\cdot A_1C_1}{A_1B_1}=\frac{"
            + bracket(q["A1K"])
            + r"\cdot "
            + bracket(q["top_diagonal"])
            + "}{"
            + value(q["a"])
            + "}="
            + value(q["A1T"])
        )
        + line(
            r"TB_1=A_1B_1-TA_1="
            + value(q["a"])
            + "-"
            + bracket(q["A1T"])
            + "="
            + value(q["B1T"])
        )
        + line(r"\frac{A_1T}{TB_1}=" + value(m.answer))
    )


def _incidence(m):
    q = m.q
    return (
        "<p>Докажем, что D₁ лежит на построенной прямой KT. В прямоугольном треугольнике A₁D₁C₁ проекция катета A₁D₁ на гипотенузу A₁C₁ имеет длину:</p>"
        + line(
            r"\frac{A_1D_1^2}{A_1C_1}=\frac{"
            + bracket(q["b"])
            + "^2}{"
            + value(q["top_diagonal"])
            + "}="
            + value(q["A1K"])
            + "=A_1K"
        )
        + "<p>Следовательно, K — основание этого перпендикуляра, и угол A₁KD₁ прямой. Теперь применим теорему Пифагора в треугольниках TKA₁ и A₁KD₁:</p>"
        + line(
            r"TK=\sqrt{TA_1^2-A_1K^2}=\sqrt{"
            + bracket(q["A1T"])
            + "^2-"
            + bracket(q["A1K"])
            + "^2}="
            + value(q["TK"])
        )
        + line(
            r"KD_1=\sqrt{A_1D_1^2-A_1K^2}=\sqrt{"
            + bracket(q["b"])
            + "^2-"
            + bracket(q["A1K"])
            + "^2}="
            + value(q["KD1"])
        )
        + line(
            r"TK+KD_1="
            + value(q["TK"])
            + "+"
            + bracket(q["KD1"])
            + "="
            + value(q["TD1"])
        )
        + line(
            r"TD_1=\sqrt{TA_1^2+A_1D_1^2}=\sqrt{"
            + bracket(q["A1T"])
            + "^2+"
            + bracket(q["b"])
            + "^2}="
            + value(q["TD1"])
        )
        + "<p>Получили TK + KD₁ = TD₁, поэтому T, K и D₁ лежат на одной прямой. Следовательно, D₁ принадлежит плоскости α.</p>"
    )


def render(m, pictures):
    calculation = _calculation(m, pictures)
    incidence = _incidence(m)
    return (
        "<p><b>Другой способ. Геометрическое решение.</b></p>"
        '<ol data-layout="source-subparts" type="a">'
        '<li data-list-marker="б)">' + calculation + "</li>"
        '<li data-list-marker="а)">' + incidence + "</li></ol>"
    )
