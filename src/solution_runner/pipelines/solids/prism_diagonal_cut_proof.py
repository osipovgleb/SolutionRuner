"""Keep similarity, congruent right triangles and diagonal-area arguments."""

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value
from .spatial_distance_proofs import parts


def _trapezoid_first(m, pictures):
    q = m.q
    parent = m.names == ("M",)
    left, right, corner = ("M", "N", "A_1") if parent else ("L", "K", "C_1")
    upper, boundary = left + right, "BD" + left + right
    side = "D" + left
    # The parent's planar scene draws the height from N rather than M.
    if parent:
        side = "BN"
    edge = "B_1N" if parent else "D_1L"
    triangle = "BB₁N" if parent else "DD₁L"
    first = (
        pictures.get("image_1", "")
        + "<p>Проведём через заданную точку прямую, параллельную BD. Она пересекает ребро "
        + ("A₁B₁ в точке N" if parent else "C₁D₁ в точке L")
        + ". Плоскости оснований параллельны, поэтому искомое сечение — трапеция "
        + boundary
        + ".</p>"
        + "<p>Треугольник у вершины "
        + corner.replace("_1", "₁")
        + " в верхнем основании подобен треугольнику "
        + ("B₁A₁D₁" if parent else "D₁C₁B₁")
        + ". Коэффициент подобия равен доле оставшейся части ребра:</p>"
        + line(
            r"\frac{"
            + upper
            + r"}{B_1D_1}=\frac{"
            + corner
            + left
            + r"}{"
            + corner
            + r"D_1}="
            + value(q["fraction"])
        )
        + line(
            r"BD=B_1D_1=AB\sqrt{2}="
            + bracket(q["a"])
            + r"\sqrt{2}="
            + value(q["diagonal"])
        )
        + line(
            upper
            + "="
            + bracket(q["fraction"])
            + r"\cdot "
            + bracket(q["diagonal"])
            + "="
            + value(q["upper"])
        )
        + "<p>В прямоугольных треугольниках BB₁"
        + right
        + " и DD₁"
        + left
        + " вертикальные катеты равны высоте призмы, а горизонтальные — равным остаткам верхних рёбер. Поэтому треугольники равны по двум катетам, и трапеция равнобедренная.</p>"
        + line(
            edge
            + "="
            + bracket(q["a"])
            + r"\cdot(1-"
            + value(q["fraction"])
            + ")="
            + value(q["edge_part"])
        )
        + "<p>По теореме Пифагора в треугольнике "
        + triangle
        + ":</p>"
        + line(
            side
            + r"=\sqrt{"
            + bracket(q["height"])
            + "^2+"
            + bracket(q["edge_part"])
            + "^2}="
            + value(q["side"])
        )
    )
    return first


def _trapezoid_height(m, pictures):
    q = m.q
    parent = m.names == ("M",)
    upper, boundary = ("MN", "BDMN") if parent else ("LK", "BDLK")
    side, height, foot = ("BN", "NH", "BH") if parent else ("DL", "LH", "DH")
    return (
        "<p>Пусть "
        + height
        + " — высота трапеции к основанию BD. В равнобедренной трапеции отрезок "
        + foot
        + " равен половине разности оснований.</p>"
        + pictures.get("image_2", "")
        + line(
            foot
            + r"=\frac{BD-"
            + upper
            + r"}{2}=\frac{"
            + value(q["diagonal"])
            + "-"
            + bracket(q["upper"])
            + "}{2}="
            + value(q["offset"])
        )
        + line(
            height
            + r"=\sqrt{"
            + side
            + "^2-"
            + foot
            + r"^2}=\sqrt{"
            + bracket(q["side"])
            + "^2-"
            + bracket(q["offset"])
            + "^2}="
            + value(q["altitude"])
        )
        + line("S_{" + boundary + r"}=\frac{BD+" + upper + r"}{2}\cdot " + height)
        + line(
            "S_{"
            + boundary
            + r"}=\frac{"
            + value(q["diagonal"])
            + "+"
            + bracket(q["upper"])
            + r"}{2}\cdot "
            + bracket(q["altitude"])
            + "="
            + value(m.answer)
        )
    )


def _rhombus_claim(m):
    reverse = m.mode.endswith("area")
    return (
        "<p>Рассмотрим прямоугольные треугольники AMD и A₁MB₁. Поскольку призма правильная, AD = AB = A₁B₁. "
        + (
            "По условию AM = MA₁. Треугольники равны по двум катетам, поэтому MB₁ = MD. Прямые MB₁ и DK, а также MD и KB₁ параллельны как линии пересечения плоскости сечения с параллельными гранями. Следовательно, MB₁KD — параллелограмм с равными смежными сторонами, то есть ромб."
            if reverse
            else "По условию MB₁KD — ромб, поэтому MB₁ = MD. Треугольники равны по катету и гипотенузе, откуда AM = MA₁. Значит, M — середина AA₁."
        )
        + "</p>"
    )


def _rhombus_quantity(m):
    q = m.q
    result = (
        "<p>Аналогично получаем CK = KC₁. Поэтому MK параллелен диагонали AC и равен ей. Найдём диагональ сечения:</p>"
        + line(r"AB=\sqrt{S_{ABCD}}=" + value(q["a"]))
        + line(
            r"MK=AC=BD=AB\sqrt{2}="
            + bracket(q["a"])
            + r"\sqrt{2}="
            + value(q["diagonal"])
        )
    )
    if m.mode.endswith("area"):
        result += (
            "<p>Высоту призмы найдём из объёма, затем по теореме Пифагора вычислим вторую диагональ ромба:</p>"
            + line(
                r"h=\frac{V}{S_{ABCD}}=\frac{"
                + value(dict(m.given)["volume"])
                + "}{"
                + value(q["base"])
                + "}="
                + value(q["height"])
            )
            + line(
                r"B_1D=\sqrt{h^2+BD^2}=\sqrt{"
                + bracket(q["height"])
                + "^2+"
                + bracket(q["diagonal"])
                + "^2}="
                + value(q["oblique"])
            )
            + "<p>Площадь ромба равна половине произведения диагоналей:</p>"
            + line(
                r"S_{MB_1KD}=\frac{MK\cdot B_1D}{2}=\frac{"
                + bracket(q["diagonal"])
                + r"\cdot "
                + bracket(q["oblique"])
                + "}{2}="
                + value(m.answer)
            )
        )
    else:
        result += (
            "<p>Выразим вторую диагональ через площадь ромба:</p>"
            + line(r"S_{MB_1KD}=\frac{MK\cdot B_1D}{2}")
            + line(
                r"B_1D=\frac{2S_{MB_1KD}}{MK}=\frac{2\cdot "
                + bracket(q["area"])
                + "}{"
                + value(q["diagonal"])
                + "}="
                + value(q["oblique"])
            )
            + "<p>Обозначим высоту призмы через h. В прямоугольном треугольнике BB₁D по теореме Пифагора:</p>"
            + line(r"B_1D^2=h^2+BD^2")
            + line(
                r"h^2="
                + bracket(q["oblique"])
                + "^2-"
                + bracket(q["diagonal"])
                + "^2="
                + value(q["height"] ** 2)
            )
            + line("h=" + value(m.answer))
        )
    return result


def render(m, pictures):
    if m.mode == "square_prism_ratio_area":
        return parts(_trapezoid_first(m, pictures), _trapezoid_height(m, pictures))
    return parts(pictures.get("image_1", "") + _rhombus_claim(m), _rhombus_quantity(m))
