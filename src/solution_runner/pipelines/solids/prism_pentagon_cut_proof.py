"""Keep the parent projection and similarity proof with native point names."""

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value
from .spatial_distance_proofs import parts


def _midpoint(m):
    p, k = m.names
    start = (
        "<p>Опустим из "
        + p
        + " перпендикуляр "
        + p
        + p
        + "₁ на AD. Тогда "
        + p
        + "₁D = "
        + p
        + "D₁ = BC. Многогранник "
        + p
        + "₁BCD"
        + p
        + "B₁C₁D₁ — параллелепипед. Пусть плоскость сечения пересекает BB₁ в N. Противоположные грани параллельны, поэтому CN ∥ "
        + p
        + k
        + ". Эти отрезки заключены между параллельными гранями и равны. Прямоугольные треугольники CBN и "
        + p
        + k
        + "D₁ равны по катету BC = "
        + p
        + "D₁ и гипотенузе CN = "
        + p
        + k
        + ".</p>"
    )
    return (
        line(
            p
            + r"D_1=\frac{"
            + value(m.q["q"])
            + "}{"
            + value(m.q["p"] + m.q["q"])
            + r"}A_1D_1="
            + value(m.q["b"])
            + "=BC"
        )
        + start
        + line("BN=" + k + r"D_1=\frac{DD_1}{2}=\frac{BB_1}{2}")
        + "<p>Следовательно, N — середина BB₁.</p>"
    )


def _projection_height(m):
    q, (p, k) = m.q, m.names
    return (
        "<p>Продлим "
        + p
        + k
        + " в плоскости ADD₁ до пересечения с AA₁ в E. Прямая EN пересекает A₁B₁ в L. Искомое сечение — пятиугольник C"
        + k
        + p
        + "LN. Опустим CH на AD. Найдём боковую сторону основания и её проекцию:</p>"
        + line(
            r"CD=\frac{AD-BC}{2\cos60^\circ}=\frac{"
            + value(q["a"])
            + "-"
            + value(q["b"])
            + r"}{2\cdot\frac12}="
            + value(q["d"])
        )
        + line(r"HD=\frac{AD-BC}{2}=" + value(q["HD"]))
        + line(r"CH=CD\sin60^\circ=" + value(q["CH"]))
        + "<p>CH перпендикулярна плоскости ADD₁. По условию "
        + p
        + k
        + " ⟂ C"
        + k
        + ", поэтому по теореме о трёх перпендикулярах "
        + p
        + k
        + " ⟂ H"
        + k
        + ". Прямоугольные треугольники H"
        + k
        + "D и "
        + k
        + p
        + "D₁ подобны: их острые углы равны как углы с соответственно перпендикулярными сторонами. Отсюда:</p>"
        + line(r"\frac{" + k + "D_1}{" + p + r"D_1}=\frac{HD}{D" + k + "}")
        + line(
            "D"
            + k
            + r"^2="
            + p
            + r"D_1\cdot HD="
            + value(q["b"])
            + r"\cdot "
            + bracket(q["HD"])
            + "="
            + value(q["half_height"] ** 2)
        )
        + line("D" + k + "=" + value(q["half_height"]))
    )


def _sides(m):
    q, (p, k) = m.q, m.names
    return (
        "<p>В прямоугольных треугольниках "
        + p
        + k
        + "D₁ и CD"
        + k
        + " применим теорему Пифагора:</p>"
        + line(
            p
            + k
            + r"=\sqrt{"
            + p
            + "D_1^2+"
            + k
            + r"D_1^2}=\sqrt{"
            + bracket(q["b"])
            + "^2+"
            + bracket(q["half_height"])
            + "^2}="
            + value(q["length"])
        )
        + line(
            "C"
            + k
            + r"=\sqrt{CD^2+D"
            + k
            + r"^2}=\sqrt{"
            + bracket(q["d"])
            + "^2+"
            + bracket(q["half_height"])
            + "^2}="
            + value(q["width"])
        )
    )


def _projection_area(m):
    q, (p, k) = m.q, m.names
    return (
        "<p>Треугольники "
        + p
        + k
        + "D₁ и "
        + p
        + "EA₁ подобны по двум углам. Аналогично подобны LNB₁ и LEA₁. Поэтому:</p>"
        + line(
            r"\frac{EL}{LN}=\frac{A_1E}{NB_1}=\frac{E"
            + p
            + "}{"
            + k
            + p
            + r"}=\frac{A_1"
            + p
            + "}{"
            + p
            + "D_1}="
            + value(q["d"] / q["b"])
        )
        + line(
            "E"
            + p
            + "="
            + bracket(q["d"] / q["b"])
            + r"\cdot "
            + bracket(q["length"])
            + "="
            + value(q["EM"])
        )
        + line(r"LN=\frac{" + value(q["b"]) + "}{" + value(q["a"]) + "}EN")
        + "<p>Параллелограмм C"
        + k
        + p
        + "N — прямоугольник: по условию его смежные стороны перпендикулярны. Треугольники "
        + p
        + "LN и E"
        + p
        + "N имеют общую высоту к EN, а их основания относятся как LN : EN. Сложим площадь прямоугольника и треугольника:</p>"
        + line(
            "S_{C"
            + k
            + p
            + "N}=C"
            + k
            + r"\cdot "
            + k
            + p
            + "="
            + value(q["width"] * q["length"])
        )
        + line(
            "S_{"
            + p
            + r"LN}=\frac{"
            + value(q["b"])
            + "}{"
            + value(q["a"])
            + "}S_{E"
            + p
            + r"N}=\frac{"
            + value(q["b"])
            + "}{"
            + value(q["a"])
            + r"}\cdot\frac{"
            + bracket(q["EM"])
            + r"\cdot "
            + bracket(q["width"])
            + "}{2}="
            + value(q["b"] * q["EM"] * q["width"] / (2 * q["a"]))
        )
        + line(
            "S_{C"
            + k
            + p
            + r"LN}=S_{C"
            + k
            + p
            + "N}+S_{"
            + p
            + "LN}="
            + value(m.answer)
        )
    )


def render(m, pictures):
    second = _projection_height(m) + _sides(m) + _projection_area(m)
    return parts(
        pictures.get("image_1", pictures.get("box_distance_solution", ""))
        + _midpoint(m),
        second,
    )
