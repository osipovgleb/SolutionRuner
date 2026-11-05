"""Keep the parent's cosine-law quartic followed by its shorter projection remark."""

import sympy as sp

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value
from .spatial_distance_proofs import parts
from .spatial_metric_proofs import picture


def _lengths(m):
    q = m.q
    a, b, c, _ = m.names
    angle = r"\angle " + b + a + c
    bc = b + c
    ce = c + "E"
    be = b + "E"
    result = ""
    if m.names[-1] == "angle":
        result += line(
            angle
            + r"=180^{\circ}-90^{\circ}-"
            + value(q["given_angle"])
            + r"^{\circ}="
            + value(q["a_angle"])
            + r"^{\circ}"
        )
    result += line(bc + "=" + a + c + r"\cdot\tan " + angle)
    result += line(
        bc
        + "="
        + bracket(q["c"])
        + r"\cdot "
        + bracket(q["sin"] / q["cos"])
        + "="
        + value(q["BC"])
    )
    result += line(
        be
        + "="
        + bc
        + r"\sin "
        + angle
        + "="
        + bracket(q["BC"])
        + r"\cdot "
        + bracket(q["sin"])
        + "="
        + value(q["BE"])
    )
    result += line(
        ce
        + "="
        + bc
        + r"\cos "
        + angle
        + "="
        + bracket(q["BC"])
        + r"\cdot "
        + bracket(q["cos"])
        + "="
        + value(q["CE"])
    )
    return result


def _quartic(m):
    q = m.q
    _, b, c, _ = m.names
    diagonal = c + b + "_1"
    projection = b + "_1E"
    ce = c + "E"
    x = sp.Symbol("x")
    bb = q["BC"] ** 2
    be = q["BE"] ** 2
    h2 = q["H"] ** 2
    polynomial = sp.expand((x * x + be) * (x * x - h2))
    return (
        "<p>Обозначим высоту призмы через x, причём x &gt; 0. По теореме Пифагора в двух прямоугольных треугольниках:</p>"
        + line(diagonal + r"=\sqrt{x^2+" + value(bb) + "}")
        + line(projection + r"=\sqrt{x^2+" + value(be) + "}")
        + "<p>Применим теорему косинусов к треугольнику "
        + b
        + "₁"
        + c
        + "E, где угол при "
        + b
        + "₁ равен "
        + value(q["beta"])
        + "°. Подставим найденные длины:</p>"
        + line(
            ce
            + "^2="
            + diagonal
            + "^2+"
            + projection
            + "^2-2"
            + diagonal
            + r"\cdot "
            + projection
            + r"\cos "
            + value(q["beta"])
            + r"^{\circ}"
        )
        + line(
            value(q["CE"] ** 2)
            + "=2x^2+"
            + value(bb + be)
            + r"-2\cdot "
            + bracket(q["cos_beta"])
            + r"\sqrt{(x^2+"
            + value(bb)
            + r")(x^2+"
            + value(be)
            + ")}"
        )
        + "<p>Перенесём слагаемые и разделим на положительный коэффициент. Обе части полученного равенства неотрицательны, поэтому можно возвести его в квадрат:</p>"
        + line(
            r"\sqrt{(x^2+"
            + value(bb)
            + ")(x^2+"
            + value(be)
            + r")}=\frac{x^2+"
            + value(be)
            + "}{"
            + value(q["cos_beta"])
            + "}"
        )
        + line(
            bracket(q["cos_beta"])
            + r"^2(x^2+"
            + value(bb)
            + ")(x^2+"
            + value(be)
            + ")=(x^2+"
            + value(be)
            + ")^2"
        )
        + line(sp.latex(polynomial) + "=0")
        + line("(x^2+" + value(be) + ")(x^2-" + value(h2) + ")=0")
        + "<p>Равенство x² = −"
        + value(be)
        + " невозможно для действительного x. Остаётся положительная высота:</p>"
        + line("x^2=" + value(h2))
        + line("x=" + value(q["H"]))
    )


def _remark(m):
    q = m.q
    _, b, c, _ = m.names
    diagonal = c + b + "_1"
    height = b + b + "_1"
    return (
        "<p><b>Примечание.</b> Можно использовать прямоугольность треугольника "
        + b
        + "₁E"
        + c
        + ", доказанную в пункте а). Катет "
        + c
        + "E лежит напротив угла "
        + value(q["beta"])
        + "°, поэтому:</p>"
        + line(
            diagonal
            + r"=\frac{"
            + c
            + r"E}{\sin "
            + value(q["beta"])
            + r"^{\circ}}=\frac{"
            + value(q["CE"])
            + "}{"
            + value(q["sin_beta"])
            + "}="
            + value(q["diagonal"])
        )
        + "<p>Затем найдём высоту призмы по теореме Пифагора:</p>"
        + line(height + r"=\sqrt{" + diagonal + "^2-" + b + c + "^2}")
        + line(
            height
            + r"=\sqrt{"
            + bracket(q["diagonal"])
            + "^2-"
            + bracket(q["BC"])
            + "^2}="
            + value(q["H"])
        )
    )


def render(m, pictures):
    q = m.q
    a, b, c, claim = m.names
    plane = a + a + "_1" + b + "_1"
    angle = r"\angle " + c + b + "_1E"
    proof = (
        "<p>Высота "
        + c
        + "E основания перпендикулярна "
        + a
        + b
        + " и вертикальной прямой, проведённой через E в плоскости "
        + plane.replace("_1", "₁")
        + ". Поэтому "
        + c
        + "E перпендикулярна этой плоскости и, в частности, прямой "
        + b
        + "₁E.</p>"
    )
    proof += line(r"\angle " + b + "_1E" + c + r"=90^{\circ}")
    if claim == "angle":
        proof += (
            "<p>Проекция "
            + b
            + "₁"
            + c
            + " на эту плоскость — "
            + b
            + "₁E. По определению угла между прямой и плоскостью:</p>"
            + line(angle + "=" + value(q["beta"]) + r"^{\circ}")
        )
    calculation = (
        "<p>Найдём сначала стороны прямоугольного треугольника основания и его высоту. Используем равенство острых углов с взаимно перпендикулярными сторонами:</p>"
        + _lengths(m)
        + _quartic(m)
        + _remark(m)
    )
    return (
        "<p>Введём обозначения, как показано на рисунке.</p>"
        + picture(pictures)
        + parts(proof, calculation)
    )
