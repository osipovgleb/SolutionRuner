"""The parent's perpendicular foot gives the line-to-plane angle."""

import sympy as sp

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value
from .spatial_distance_proofs import parts


def _claim(m):
    if m.names[1] == "equal_faces":
        return (
            "<p>Противоположные грани прямоугольного параллелепипеда — равные прямоугольники, поэтому их диагонали равны:</p>"
            + line(r"AC=B_1D_1,\qquad CB_1=AD_1,\qquad AB_1=CD_1")
            + "<p>Каждая грань тетраэдра ACB₁D₁ содержит по одному отрезку из каждой пары равных противоположных рёбер. Следовательно, все четыре грани равны по трём сторонам.</p>"
        )
    return (
        line("AB=BC=" + value(m.q["a"]))
        + "<p>Основание ABCD — квадрат, поэтому AC ⟂ BD. Кроме того, AA₁ перпендикулярна основанию и направлению BD. Через точку пересечения диагоналей проведём прямую, параллельную AA₁: она лежит в плоскости AA₁C и также перпендикулярна BD. Значит, BD ⟂ AA₁C. Плоскость DA₁B содержит BD, поэтому по признаку перпендикулярности плоскостей DA₁B ⟂ AA₁C.</p>"
    )


def _face(m):
    q = m.q
    diagonal = sp.sqrt(q["a"] ** 2 + q["height"] ** 2)
    return (
        "<p>Сечение плоскостью A₁BC — прямоугольник A₁BCD₁. Опустим из C₁ перпендикуляр C₁H на CD₁. Он лежит в грани DCC₁D₁, перпендикулярной CB. Поэтому C₁H перпендикулярен и прямой через H, параллельной CB. Эта прямая и CD₁ лежат в плоскости сечения, значит, C₁H ⟂ A₁BC. Отрезок BH — проекция BC₁ на эту плоскость, и искомый угол равен C₁BH.</p>"
        + "<p>В прямоугольном треугольнике D₁C₁C найдём высоту к гипотенузе через площадь:</p>"
        + line(
            r"CD_1=\sqrt{D_1C_1^2+CC_1^2}=\sqrt{"
            + bracket(q["a"])
            + "^2+"
            + bracket(q["height"])
            + "^2}="
            + value(diagonal)
        )
        + line(
            r"C_1H=\frac{D_1C_1\cdot CC_1}{CD_1}=\frac{"
            + bracket(q["a"])
            + r"\cdot "
            + bracket(q["height"])
            + "}{"
            + bracket(diagonal)
            + "}="
            + value(q["helper"])
        )
        + "<p>По теореме Пифагора в прямоугольном треугольнике BCC₁:</p>"
        + line(
            r"BC_1=\sqrt{BC^2+CC_1^2}=\sqrt{"
            + bracket(q["b"])
            + "^2+"
            + bracket(q["height"])
            + "^2}="
            + value(q["hypotenuse"])
        )
        + "<p>В прямоугольном треугольнике BC₁H:</p>"
        + line(
            r"\sin\angle C_1BH=\frac{C_1H}{BC_1}=\frac{"
            + bracket(q["helper"])
            + "}{"
            + bracket(q["hypotenuse"])
            + "}="
            + value(q["sine"])
        )
    )


def _diagonal(m):
    q = m.q
    diagonal = sp.sqrt(q["a"] ** 2 + q["b"] ** 2)
    return (
        "<p>Опустим из B перпендикуляр BH на AC. Он лежит в основании и потому перпендикулярен направлению AA₁. Через H проведём в плоскости AA₁C прямую, параллельную AA₁. Она и AC перпендикулярны BH, следовательно, BH ⟂ AA₁C. Проекция A₁B на эту плоскость — отрезок A₁H. Искомый угол равен BA₁H.</p>"
        + "<p>В прямоугольном треугольнике ABC найдём высоту к гипотенузе:</p>"
        + line(
            r"AC=\sqrt{AB^2+BC^2}=\sqrt{"
            + bracket(q["a"])
            + "^2+"
            + bracket(q["b"])
            + "^2}="
            + value(diagonal)
        )
        + line(
            r"BH=\frac{AB\cdot BC}{AC}=\frac{"
            + bracket(q["a"])
            + r"\cdot "
            + bracket(q["b"])
            + "}{"
            + bracket(diagonal)
            + "}="
            + value(q["helper"])
        )
        + "<p>В прямоугольном треугольнике A₁AB:</p>"
        + line(
            r"A_1B=\sqrt{AA_1^2+AB^2}=\sqrt{"
            + bracket(q["height"])
            + "^2+"
            + bracket(q["a"])
            + "^2}="
            + value(q["hypotenuse"])
        )
        + "<p>Найдём синус искомого угла в прямоугольном треугольнике A₁HB:</p>"
        + line(
            r"\sin\angle BA_1H=\frac{BH}{A_1B}=\frac{"
            + bracket(q["helper"])
            + "}{"
            + bracket(q["hypotenuse"])
            + "}="
            + value(q["sine"])
        )
    )


def _midpoint_dimensions(m):
    dimensions = []
    for label, dimension in (("AB", "a"), ("AD", "b"), (r"AA_1", "height")):
        decimal = m.symbols.get(dimension + "_decimal")
        dimensions.append(
            label + "=" + (decimal + "=" if decimal else "") + sp.latex(m.q[dimension])
        )
    return line(r",\qquad ".join(dimensions))


def _exact_bracket(number):
    return r"\left(" + sp.latex(number) + r"\right)"


def _midpoint(m):
    q = m.q
    side = m.names[0] == "midpoint_side"
    normal, projected, angle = (
        ("BE", "BF", "EFB") if side else (r"A_1E", r"A_1F", r"EFA_1")
    )
    key, other = ("a", "b") if side else ("height", "a")
    introduction = (
        "<p>Плоскость ADD₁ параллельна грани BB₁C₁C. Поэтому найдём угол между EF и этой гранью. Так как E лежит на AB, её проекция — точка B. Проекция EF — прямая BF, а искомый угол — EFB.</p>"
        if side
        else "<p>Плоскость ABC параллельна верхнему основанию A₁B₁C₁D₁. Найдём угол между EF и этим основанием. Точка A₁ — проекция E, поэтому проекция EF — прямая A₁F. Искомый угол — EFA₁.</p>"
    )
    return (
        introduction
        + "<p>Противоположные рёбра прямоугольного параллелепипеда равны. Из данных условия:</p>"
        + _midpoint_dimensions(m)
        + "<p>Используем, что E и F — середины соответствующих рёбер:</p>"
        + line(
            normal
            + r"=\frac{"
            + ("AB" if side else r"AA_1")
            + r"}{2}=\frac{"
            + sp.latex(q[key])
            + "}{2}="
            + sp.latex(q["normal_leg"])
        )
        + line(
            (r"B_1F=\frac{BC}{2}=" if side else r"D_1F=\frac{AB}{2}=")
            + sp.latex(q[other] / 2)
        )
        + "<p>По теореме Пифагора в прямоугольном треугольнике:</p>"
        + line(
            projected
            + (r"=\sqrt{BB_1^2+B_1F^2}" if side else r"=\sqrt{A_1D_1^2+D_1F^2}")
        )
        + line(
            projected
            + r"=\sqrt{"
            + _exact_bracket(q["height"] if side else q["b"])
            + "^2+"
            + _exact_bracket(q[other] / 2)
            + "^2}="
            + sp.latex(q["projection"])
        )
        + "<p>Тангенс угла в полученном прямоугольном треугольнике:</p>"
        + line(
            r"\tan\angle "
            + angle
            + r"=\frac{"
            + normal
            + "}{"
            + projected
            + r"}=\frac{"
            + _exact_bracket(q["normal_leg"])
            + "}{"
            + _exact_bracket(q["projection"])
            + "}="
            + sp.latex(q["tan"])
        )
    )


def render(m, pictures):
    picture = pictures.get("image_1", pictures.get("box_distance_solution", ""))
    return parts(
        picture + _claim(m),
        _midpoint(m)
        if m.names[0].startswith("midpoint_")
        else _face(m)
        if m.names[0] == "face"
        else _diagonal(m),
    )
