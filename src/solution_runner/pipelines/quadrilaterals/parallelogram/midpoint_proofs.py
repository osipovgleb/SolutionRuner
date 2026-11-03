"""Keep the parent's ordered height, median and Varignon methods."""

from ...probability.common import line
from ...triangles.right.altitude_methods import solution_section
from ...triangles.right.altitude_parent import exact_answer
from .midpoint_model import HEIGHT, TWO_TRAPEZOID, TWO_TRIANGLE


def _number(value):
    return exact_answer(value).replace(",", "{,}")


def _area(name):
    return "S_{" + name + "}"


def _trapezoid(m, picture, *, one_method=False):
    n, s = m.name, _area(m.target)
    base = m.midpoint
    small = "E" + n("A") if one_method else n("AE")
    opposite = "".join(sorted(n("BC")))
    introduction = (
        "Пусть h — высота параллелограмма ABCD, тогда его площадь равна произведению длины основания на высоту:"
        if one_method
        else "Площадь параллелограмма равна произведению длины его основания на длину высоты:"
    )
    return (
        picture
        + "<p>"
        + introduction
        + "</p>"
        + line(r"S_{ABCD}=" + base + r"\cdot h")
        + f"<p>Точка E — середина стороны {base}, а противоположные стороны параллелограмма равны. Площадь трапеции равна полусумме длин оснований, умноженной на длину высоты. Выразим площадь трапеции через площадь параллелограмма:</p>"
        + line(small + r"=\frac{1}{2}" + base)
        + line(opposite + "=" + base)
        + line(s + r"=\frac{" + small + "+" + opposite + r"}{2}\cdot h")
        + line(s + r"=\frac{\frac{1}{2}" + base + "+" + base + r"}{2}\cdot h")
        + line(s + r"=\frac{3}{4}" + base + r"\cdot h")
        + line(s + r"=\frac{3}{4}S_{ABCD}")
        + line(s + r"=\frac{3}{4}\cdot " + _number(m.given) + "=" + _number(m.answer))
    )


def _trapezoid_median(m, picture):
    n, s = m.name, _area(m.target)
    first, second, corner = [_area(n(t)) for t in ("ABC", "ACD", "CDE")]
    return (
        picture
        + f"<p>Диагональ {n('AC')} разбивает параллелограмм ABCD на два равных треугольника, значит:</p>"
        + line(first + "=" + second)
        + line(second + r"=\frac{S_{ABCD}}{2}")
        + f"<p>Медиана {n('CE')} разбивает треугольник {n('ACD')} на два равновеликих треугольника:</p>"
        + line(corner + r"=\frac{" + second + "}{2}")
        + line(corner + r"=\frac{S_{ABCD}}{4}")
        + f"<p>Тогда для трапеции {m.target} получаем:</p>"
        + line(s + "=S_{ABCD}-" + corner)
        + line(s + r"=S_{ABCD}-\frac{S_{ABCD}}{4}")
        + line(s + "=" + _number(m.given) + r"-\frac{" + _number(m.given) + "}{4}")
        + line(s + "=" + _number(m.answer))
    )


def _triangle_height(m, picture):
    n, s = m.name, _area(m.target)
    height, side, half = n("AH"), n("DC"), n("DE")
    return (
        picture
        + f"<p>Пусть отрезок {height} — перпендикуляр, опущенный из точки {n('A')} на продолжение стороны {n('CD')} за точку {n('D')}. Выразим площадь треугольника {m.target} через площадь параллелограмма ABCD:</p>"
        + line(half + r"=\frac{1}{2}" + side)
        + line(r"S_{ABCD}=" + height + r"\cdot " + side)
        + line(s + r"=\frac{1}{2}" + height + r"\cdot " + half)
        + line(s + r"=\frac{1}{2}" + height + r"\cdot\frac{1}{2}" + side)
        + line(s + r"=\frac{1}{4}" + height + r"\cdot " + side)
        + line(s + r"=\frac{1}{4}S_{ABCD}")
        + line(s + r"=\frac{1}{4}\cdot " + _number(m.given))
        + line(s + "=" + _number(m.answer))
    )


def _triangle_median(m):
    n, s = m.name, _area(m.target)
    half = _area(n("ADC"))
    return (
        f"<p>Диагональ {n('AC')} делит параллелограмм на два равных треугольника, площадь каждого из которых равна половине площади параллелограмма:</p>"
        + line(half + r"=\frac{S_{ABCD}}{2}")
        + f"<p>Медиана {n('AE')} делит треугольник {n('ADC')} на два равновеликих треугольника. Следовательно, площадь треугольника {m.target} равна четверти площади параллелограмма:</p>"
        + line(s + r"=\frac{" + half + "}{2}")
        + line(s + r"=\frac{\frac{S_{ABCD}}{2}}{2}")
        + line(s + r"=\frac{S_{ABCD}}{4}")
        + line(s + r"=\frac{" + _number(m.given) + "}{4}")
        + line(s + "=" + _number(m.answer))
    )


def _varignon(m, picture):
    s = _area(m.target)
    return (
        picture
        + "<p>Четырёхугольник, вершинами которого являются середины сторон произвольного четырёхугольника, является параллелограммом, площадь которого равна половине площади исходного четырёхугольника (параллелограмм Вариньона). Поясним соотношение площадей: на рисунке A′ и B′ — середины сторон AD и AB. Треугольник AA′B′ подобен треугольнику ADB с коэффициентом 1/2:</p>"
        + line(r"S_{ADB}=\frac{S_{ABCD}}{2}")
        + line(r"\frac{S_{AA'B'}}{S_{ADB}}=\left(\frac{1}{2}\right)^2=\frac{1}{4}")
        + line(r"S_{AA'B'}=\frac{1}{4}\cdot\frac{S_{ABCD}}{2}=\frac{S_{ABCD}}{8}")
        + "<p>Каждый из четырёх угловых треугольников имеет такую же площадь. Вычтем их площади из площади исходного параллелограмма:</p>"
        + line(s + r"=S_{ABCD}-4\cdot\frac{S_{ABCD}}{8}")
        + line(s + r"=S_{ABCD}-\frac{S_{ABCD}}{2}")
        + line(s + r"=\frac{S_{ABCD}}{2}")
        + line(s + r"=\frac{" + _number(m.given) + "}{2}")
        + line(s + "=" + _number(m.answer))
    )


def render(m, rule, pictures):
    if rule in {TWO_TRAPEZOID, HEIGHT}:
        first = _trapezoid(m, pictures.get("height", ""), one_method=rule == HEIGHT)
        second = (
            _trapezoid_median(m, pictures["median"]) if rule == TWO_TRAPEZOID else None
        )
    elif rule == TWO_TRIANGLE:
        first, second = _triangle_height(m, pictures["height"]), _triangle_median(m)
    else:
        first, second = _varignon(m, pictures["varignon"]), None
    return solution_section("Решение", first) + (
        solution_section("Приведём другое решение", second) if second else ""
    )
