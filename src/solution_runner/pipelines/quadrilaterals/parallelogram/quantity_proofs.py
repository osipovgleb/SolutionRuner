"""Preserve the parent's height methods and adapt projection remarks to the child."""

from ...probability.common import line
from ...triangles.right.altitude_methods import solution_section
from .rectangle_proofs import bracket, value
from .rhombus_quantity_proofs import render as render_rhombus


def _projection(m, name, base):
    if m.projection == 0:
        return line(name + "=0")
    operator = r"\gt" if m.projection > m.a else r"\lt" if m.projection < m.a else "="
    return (
        line(name + r"=\sqrt{" + bracket(m.b) + "^2-" + bracket(m.first_height) + "^2}")
        + line(name + "=" + value(m.projection))
        + line(name + operator + " " + base)
    )


def _sine(m):
    n = m.name
    height, projection, base, side = n("DH"), n("AH"), n("AB"), n("AD")
    intro = (
        "Большая высота проведена к меньшей стороне " + base + "."
        if m.a < m.b
        else "Стороны равны, поэтому обе высоты равны. Рассчитаем высоту к стороне "
        + base
        + "."
    )
    location = (
        "H совпадает с A: угол A прямой."
        if m.projection == 0
        else "H лежит на продолжении стороны " + base + " за точкой " + n("B") + "."
        if m.projection > m.a
        else "H совпадает с точкой " + n("B") + "."
        if m.projection == m.a
        else "H лежит внутри стороны " + base + "."
    )
    geometry = (
        "Угол A прямой; основание высоты совпадает с A."
        if m.sine == 1
        else "На рисунке выбрана допустимая конфигурация с острым углом A. При тупом A основание H лежит на продолжении за A; длина высоты остаётся той же. Проверим положение H в изображённом случае по теореме Пифагора:"
    )
    first = (
        "<p>"
        + intro
        + " Опустим перпендикуляр из точки "
        + n("D")
        + " к прямой "
        + base
        + "; его основание обозначим H. Имеем:</p>"
        + line(side + "=" + value(m.b))
        + line(r"\sin A=" + value(m.sine))
        + line(height + "=" + side + r"\sin A")
        + line(height + "=" + value(m.b) + r"\cdot " + bracket(m.sine))
        + line(height + "=" + value(m.answer))
        + "<p><b>Приведём примечание Дмитрия Д.</b></p><p>"
        + geometry
        + "</p>"
        + (
            line(projection + r"=\sqrt{" + side + "^2-" + height + "^2}")
            if m.projection != 0
            else ""
        )
        + _projection(m, projection, base)
        + "<p>"
        + location
        + " Положение основания высоты не меняет использованную формулу её длины.</p>"
    )
    second = (
        "<p>Найдём площадь параллелограмма. Обозначим меньшую из сторон a, другую b. При равных сторонах положим a=b:</p>"
        + line("a=" + value(m.a) + r",\quad b=" + value(m.b))
        + line(r"\sin A=" + value(m.sine))
        + line(r"S=ab\sin A")
        + line("S=" + value(m.a) + r"\cdot " + value(m.b) + r"\cdot " + bracket(m.sine))
        + line("S=" + value(m.area))
        + "<p>Чтобы найти высоту h к основанию a, воспользуемся другой формулой площади:</p>"
        + line("S=ah")
        + line(r"h=\frac{S}{a}")
        + line(r"h=\frac{" + value(m.area) + "}{" + value(m.a) + "}")
        + line("h=" + value(m.answer))
    )
    return solution_section("Решение", first) + solution_section(
        "Альтернативное решение.", second
    )


def _transfer(m, pictures):
    location = (
        "Угол прямой, поэтому G совпадает с C."
        if m.projection == 0
        else "Основание G лежит на продолжении CD за D; положение G на исходной схеме для этих данных неверно."
        if m.projection > m.a
        else "Основание G совпадает с D."
        if m.projection == m.a
        else "Основание G лежит на стороне CD. Положение G на исходной схеме соответствует данным; выносить G за точку D не требуется."
    )
    h = m.first_height
    angle = (
        "Угол A прямой."
        if m.sine == 1
        else "Для рисунка выбрана конфигурация с острым углом A; длины обеих высот при тупом угле A остаются такими же."
    )
    return solution_section(
        "Решение",
        "<p>Пусть x — длина искомой высоты, a — основание с известной высотой h, b — второе основание. Площадь параллелограмма равна произведению основания на опущенную на него высоту. Вычислим площадь двумя способами:</p>"
        + line("a=" + value(m.a) + r",\quad h=" + value(h))
        + line("S=ah")
        + line("S=" + value(m.a) + r"\cdot " + value(h))
        + line("S=" + value(m.area))
        + line("S=bx")
        + line("b=" + value(m.b))
        + "<p>Из полученного уравнения найдём искомую высоту:</p>"
        + line(r"x=\frac{S}{b}")
        + line(r"x=\frac{" + value(m.area) + "}{" + value(m.b) + "}=" + value(m.answer))
        + "<p>Исходная схема с основаниями высот на сторонах; проверим её для данных задачи:</p>"
        + pictures["reference"]
        + "<p><b>Примечание.</b></p><p>"
        + angle
        + " Проверим длину проекции CG на прямую CD. При непрямом угле применяем теорему Пифагора к треугольнику BGC:</p>"
        + (line(r"CG=\sqrt{CB^2-BG^2}") if m.projection != 0 else "")
        + _projection(m, "CG", "CD")
        + "<p>"
        + location
        + " На уточнённой схеме нанесены длины сторон и обеих высот. Для вычисления площади положение оснований несущественно:</p>"
        + pictures["detail"],
    )


def _height(m):
    first, second = m.first_height, m.second_height
    return solution_section(
        "Решение",
        "<p>Площадь параллелограмма равна произведению основания на опущенную на него высоту. Пусть длины высот к данным сторонам равны соответственно a и b:</p>"
        + line("S=" + value(m.a) + "a")
        + line("S=" + value(m.b) + "b")
        + line("S=" + value(m.area))
        + "<p>Разделим площадь на каждую из сторон, чтобы найти обе высоты:</p>"
        + line(r"a=\frac{S}{" + value(m.a) + "}")
        + line(r"a=\frac{" + value(m.area) + "}{" + value(m.a) + "}=" + value(first))
        + line(r"b=\frac{S}{" + value(m.b) + "}")
        + line(r"b=\frac{" + value(m.area) + "}{" + value(m.b) + "}=" + value(second))
        + "<p>Сравним полученные высоты и выберем большую h:</p>"
        + line(r"h=\max(a,b)=" + value(m.answer)),
    )


def render(m, pictures):
    if m.mode == "sine":
        return _sine(m)
    if m.mode == "transfer":
        return _transfer(m, pictures)
    if m.mode == "height":
        return _height(m)
    return render_rhombus(m)
