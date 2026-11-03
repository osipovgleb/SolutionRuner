"""Keep opposite-side sums and the coloured equal-tangent cut proof."""

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value
from ..triangles.right.altitude_methods import solution_section

MODES = {
    "trapezoid_legs",
    "trapezoid_perimeter",
    "right_trapezoid_radius",
    "tangential_quad",
    "tangent_cuts",
}
PITOT = "Суммы длин противоположных сторон четырёхугольника, описанного около окружности, равны."


def _midline(m):
    intro = (
        "<p>"
        + PITOT
        + " Поэтому сумма оснований AD и BC трапеции равна сумме боковых сторон AB и CD:</p>"
    )
    if m.mode == "trapezoid_legs":
        a, b = m.given
        total = a + b
        body = (
            line("AD+BC=AB+CD")
            + line("AB+CD=" + value(a) + "+" + value(b) + "=" + value(total))
            + line("2m=AD+BC")
        )
    else:
        total = m.given[0] / 2
        body = (
            line("P=AB+BC+CD+AD")
            + line(r"AD+BC=AB+CD=\frac{P}{2}")
            + line(r"AD+BC=\frac{" + value(m.given[0]) + "}{2}=" + value(total))
        )
    return (
        intro
        + body
        + "<p>Средняя линия m трапеции равна полусумме оснований:</p>"
        + line(r"m=\frac{AD+BC}{2}")
        + line(r"m=\frac{" + value(total) + "}{2}=" + value(m.answer))
    )


def _right_trapezoid(m):
    perimeter, slant = m.given
    p, height = perimeter / 2, perimeter / 2 - slant
    return (
        "<p>Радиус окружности, вписанной в прямоугольную трапецию, равен половине её высоты, то есть половине стороны AB:</p>"
        + line(r"r=\frac{AB}{2}")
        + "<p>"
        + PITOT
        + " Каждая из этих сумм равна половине периметра:</p>"
        + line(r"AB+CD=\frac{P}{2}")
        + line(
            "AB+" + value(slant) + r"=\frac{" + value(perimeter) + "}{2}=" + value(p)
        )
        + line("AB=" + value(p) + "-" + value(slant) + "=" + value(height))
        + "<p>Разделим высоту пополам:</p>"
        + line(r"r=\frac{" + value(height) + "}{2}=" + value(m.answer))
    )


def _perimeter(m):
    a, c = m.given
    return (
        line("AB+CD=BC+AD")
        + line("AB+CD=" + value(a) + "+" + value(c) + "=" + value(a + c))
        + "<p>Сложим стороны, заменяя вторую сумму противоположных сторон первой:</p>"
        + line("P_{ABCD}=AB+BC+CD+AD")
        + line("P_{ABCD}=2(AB+CD)")
        + line(r"P_{ABCD}=2\cdot " + bracket(a + c) + "=" + value(m.answer))
    )


def _fourth(m):
    a, b, c = m.given
    p = a + c
    return (
        line("AD+BC=AB+CD")
        + line("AB+CD=" + value(a) + "+" + value(c) + "=" + value(p))
        + line("AD+" + value(b) + "=" + value(p))
        + "<p>Вычтем известную сторону BC из суммы противоположных сторон:</p>"
        + line("AD=AB+CD-BC")
        + line("AD=" + value(p) + "-" + value(b) + "=" + value(m.answer))
    )


def _opposite(m):
    perimeter, a = m.given
    return (
        line("AB+CD=BC+AD")
        + line("P_{ABCD}=2(AB+CD)")
        + line("2(" + value(a) + "+CD)=" + value(perimeter))
        + "<p>Разделим обе части на два и вычтем известную сторону AB:</p>"
        + line(value(a) + "+CD=" + value(perimeter / 2))
        + line("CD=" + value(perimeter / 2) + "-" + value(a) + "=" + value(m.answer))
    )


def _larger(m):
    perimeter, a, b = m.given
    p = perimeter / 2
    return (
        "<p>Периметр вдвое больше суммы длин противоположных сторон. Обозначим известные стороны через a и b:</p>"
        + line(r"p=\frac{P_{ABCD}}{2}=\frac{" + value(perimeter) + "}{2}=" + value(p))
        + line("a+b=" + value(a) + "+" + value(b) + "=" + value(a + b))
        + "<p>Эта сумма не равна полупериметру, поэтому известные стороны не могут быть противоположными и являются смежными. Пусть c и d — стороны, противоположные a и b соответственно:</p>"
        + line("c=p-a=" + value(p) + "-" + value(a) + "=" + value(p - a))
        + line("d=p-b=" + value(p) + "-" + value(b) + "=" + value(p - b))
        + "<p>Сравним две оставшиеся стороны:</p>"
        + line(r"\max\{c,d\}=" + value(m.answer))
    )


def _quad(m):
    methods = {
        "perimeter": _perimeter,
        "fourth_side": _fourth,
        "opposite_side": _opposite,
        "larger_side": _larger,
    }
    return "<p>" + PITOT + "</p>" + methods[m.target](m)


def _cuts(m, pictures):
    return (
        pictures["equal_tangents"]
        + "<p>Покажем, что сумма периметров отсечённых треугольников равна сумме длин сторон треугольника ABC, то есть его периметру. Отрезки касательных, проведённых к окружности из точек K, H, O, F, N, M, попарно равны; на рисунке равные отрезки выделены одинаковыми цветами. Следовательно:</p>"
        + '<p><span data-inline-latex="P_{BKM}=BQ+BR"></span>,<br/>'
        + '<span data-inline-latex="P_{CHO}=CQ+CS"></span>,<br/>'
        + '<span data-inline-latex="P_{AFN}=AS+AR"></span>.</p>'
        + "<p>Сложим правые части полученных равенств:</p>"
        + line("(BQ+BR)+(CQ+CS)+(AS+AR)=AB+BC+AC=P_{ABC}")
        + "<p>Таким образом, сложим три данных периметра:</p>"
        + line("P_{ABC}=P_{BKM}+P_{CHO}+P_{AFN}")
        + line("P_{ABC}=" + "+".join(bracket(v) for v in m.given))
        + line("P_{ABC}=" + value(m.answer))
    )


def render(m, pictures):
    if m.mode in {"trapezoid_legs", "trapezoid_perimeter"}:
        body = _midline(m)
    elif m.mode == "right_trapezoid_radius":
        body = _right_trapezoid(m)
    elif m.mode == "tangential_quad":
        body = _quad(m)
    else:
        body = _cuts(m, pictures)
    return solution_section("Решение", body)
