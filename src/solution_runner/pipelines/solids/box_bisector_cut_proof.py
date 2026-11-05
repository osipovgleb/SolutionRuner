"""Three parent methods retain both explicit directions of the edge ratio."""

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value
from .spatial_distance_proofs import parts


def _vector(m, pictures):
    q = m.q
    first = (
        pictures.get("image_1", "")
        + "<p><b>Решение при помощи векторов.</b></p>"
        + "<p>Возьмём попарно перпендикулярные базисные векторы AB, AD и AA₁. Их длины известны. Так как M — середина AC₁, получаем:</p>"
        + line(
            r"\overrightarrow{MD_1}=-\frac12\overrightarrow{AB}+\frac12\overrightarrow{AD}+\frac12\overrightarrow{AA_1}"
        )
        + line(
            r"\overrightarrow{AC_1}=\overrightarrow{AB}+\overrightarrow{AD}+\overrightarrow{AA_1}"
        )
        + line(
            r"\overrightarrow{MD_1}\cdot\overrightarrow{AC_1}=\frac12(-AB^2+AD^2+AA_1^2)"
        )
        + line(
            r"\overrightarrow{MD_1}\cdot\overrightarrow{AC_1}=\frac12(-"
            + bracket(q["a"])
            + "^2+"
            + bracket(q["b"])
            + "^2+"
            + bracket(q["height"])
            + "^2)=0"
        )
        + "<p>Следовательно, MD₁ ⟂ AC₁, и D₁ лежит в плоскости α.</p>"
    )
    second = (
        "<p>Пусть T — точка пересечения α с A₁B₁ и A₁T = t·A₁B₁. Условие MT ⟂ AC₁ даёт:</p>"
        + line(
            r"\overrightarrow{MT}=(t-\frac12)\overrightarrow{AB}-\frac12\overrightarrow{AD}+\frac12\overrightarrow{AA_1}"
        )
        + line(r"(t-\frac12)AB^2-\frac12AD^2+\frac12AA_1^2=0")
        + line(bracket(q["a"] ** 2) + "t-" + bracket(q["b"] ** 2) + "=0")
        + line(
            r"t=\frac{"
            + value(q["b"] ** 2)
            + "}{"
            + value(q["a"] ** 2)
            + "}="
            + value(q["t"])
        )
        + line(r"\frac{A_1T}{TB_1}=\frac{t}{1-t}=" + value(m.answer))
        + "<p>Это отношение дано от A₁. От B₁ получается обратное отношение:</p>"
        + line(r"\frac{B_1T}{TA_1}=" + value(1 / m.answer))
    )
    return parts(first, second)


def _coordinate(m, pictures):
    q = m.q
    a, b, h = (value(q[k]) for k in ("a", "b", "height"))
    first = (
        pictures.get("image_2", "")
        + "<p><b>Решение методом координат.</b></p>"
        + "<p>Начало координат выберем в B, оси направим вдоль BA, BC и BB₁. В этой системе:</p>"
        + line(
            "A("
            + a
            + ";0;0),\\quad C_1(0;"
            + b
            + ";"
            + h
            + "),\\quad D_1("
            + a
            + ";"
            + b
            + ";"
            + h
            + ")"
        )
        + line(
            "M("
            + value(q["a"] / 2)
            + ";"
            + value(q["b"] / 2)
            + ";"
            + value(q["height"] / 2)
            + ")"
        )
        + line(r"\overrightarrow{AC_1}=(-" + a + ";" + b + ";" + h + ")")
        + "<p>Вектор AC₁ — нормаль к α. Плоскость проходит через M, поэтому:</p>"
        + line(
            "-"
            + bracket(q["a"])
            + "(x-"
            + bracket(q["a"] / 2)
            + ")+"
            + bracket(q["b"])
            + "(y-"
            + bracket(q["b"] / 2)
            + ")+"
            + bracket(q["height"])
            + "(z-"
            + bracket(q["height"] / 2)
            + ")=0"
        )
        + line(
            "-"
            + bracket(q["a"])
            + "x+"
            + bracket(q["b"])
            + "y+"
            + bracket(q["height"])
            + "z=0"
        )
        + "<p>Подставим координаты D₁:</p>"
        + line(
            "-"
            + bracket(q["a"])
            + "^2+"
            + bracket(q["b"])
            + "^2+"
            + bracket(q["height"])
            + "^2=0"
        )
        + "<p>Значит, D₁ принадлежит α.</p>"
    )
    second = (
        "<p>Пусть u — первая координата точки T. Подставим её координаты в уравнение плоскости:</p>"
        + line("T(u;0;" + h + ")")
        + line("-" + bracket(q["a"]) + "u+" + bracket(q["height"]) + "^2=0")
        + line(
            r"u=\frac{" + value(q["height"] ** 2) + "}{" + a + "}=" + value(q["B1T"])
        )
        + line(r"B_1T=u=" + value(q["B1T"]))
        + line(r"TA_1=BA-B_1T=" + a + "-" + bracket(q["B1T"]) + "=" + value(q["A1T"]))
        + line(r"\frac{B_1T}{TA_1}=" + value(1 / m.answer))
        + line(r"\frac{A_1T}{TB_1}=" + value(m.answer))
    )
    note = (
        pictures.get("image_3", "")
        + "<p><b>Построение сечения.</b> Точка M — центр симметрии параллелепипеда. Плоскость α проходит через M, поэтому вместе с D₁ содержит симметричную ей вершину B. Отрезок TD₁ задаёт след сечения на верхнем основании; в противоположных гранях проводим параллельные ему стороны.</p>"
    )
    return parts(first, second) + note


def render(m, pictures):
    from .box_bisector_geometric_proof import render as geometric

    return _vector(m, pictures) + _coordinate(m, pictures) + geometric(m, pictures)
