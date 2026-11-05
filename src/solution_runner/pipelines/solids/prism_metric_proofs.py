"""Use the parents' planar geometry, parallel translations and right triangles."""

import sympy as sp

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value
from . import regular_prism_geometry as g


def _math(text):
    return '<span data-inline-latex="' + text + '"></span>'


def _chord(m):
    segment = "".join(m.requested)
    return (
        "<p>Длина большей диагонали правильного шестиугольника равна его удвоенной стороне. Обозначим сторону через a, радиус описанной окружности — через R:</p>"
        + line("a=" + value(m.edge))
        + line("R=a")
        + line(segment + "=2R")
        + "<p>Искомый отрезок соединяет противоположные вершины основания. Подставим длину стороны:</p>"
        + line(segment + "=2a")
        + line(segment + r"=2\cdot" + bracket(m.edge) + "=" + value(m.answer))
    )


def _distance(m):
    a, b = m.requested
    foot = m.helper[0]
    vertical, chord = a + foot, foot + b
    length = sp.simplify(sp.sqrt(g.squared(m.points, chord)))
    short = length == sp.sqrt(3)
    opening = (
        "<p>Рассмотрим прямоугольный треугольник "
        + _math(a + foot + b)
        + ". По теореме Пифагора:</p>"
        + line(a + b + "^2=" + vertical + "^2+" + chord + "^2")
        + line("a=" + value(m.edge))
    )
    if short:
        calculation = (
            "<p>Угол между сторонами правильного шестиугольника равен 120°. Для короткой диагонали основания по теореме косинусов получаем:</p>"
            + line(chord + r"^2=a^2+a^2-2a^2\cos120^{\circ}")
            + line(chord + "^2=3a^2")
        )
    else:
        calculation = (
            "<p>Катет "
            + _math(chord)
            + " — большая диагональ правильного шестиугольника, её длина равна удвоенной стороне:</p>"
            + line(chord + "=2a")
            + line(chord + "^2=4a^2")
        )
    return (
        opening
        + calculation
        + "<p>Боковое ребро равно стороне основания. Найдём гипотенузу:</p>"
        + line(vertical + "=a")
        + line(
            a
            + b
            + r"=\sqrt{"
            + bracket(m.edge)
            + "^2+"
            + bracket(sp.simplify(length * m.edge))
            + "^2}"
        )
        + line(
            a
            + b
            + r"=\sqrt{"
            + value(sp.simplify(m.answer**2))
            + "}="
            + value(m.answer)
        )
    )


def _bisector(m):
    angle = "".join(m.requested)
    return (
        "<p>В правильном шестиугольнике все внутренние углы равны. Найдём угол между соседними сторонами:</p>"
        + line("n=6")
        + line(r"\gamma=\frac{(n-2)180^{\circ}}{n}")
        + line(r"\gamma=\frac{4\cdot180^{\circ}}{6}=120^{\circ}")
        + "<p>Большая диагональ делит угол при вершине пополам, поэтому:</p>"
        + line(r"\angle " + angle + r"=\frac{\gamma}{2}")
        + line(r"\angle " + angle + r"=\frac{120^{\circ}}{2}=60^{\circ}")
    )


def _parallel(m):
    first, second = m.requested
    translated = "".join(m.helper)
    return (
        "<p>Отрезки "
        + _math(second)
        + " и "
        + _math(translated)
        + " лежат на параллельных прямых. Поэтому искомый угол равен углу между прямыми "
        + _math(first)
        + " и "
        + _math(translated)
        + ":</p>"
        + line(second + r"\parallel " + translated)
        + line("n=6")
        + "<p>Угол между соседними сторонами правильного шестиугольника равен 120°. Угол между прямыми — смежный с ним острый угол:</p>"
        + line(r"\gamma=\frac{(n-2)180^{\circ}}{n}=120^{\circ}")
        + line(r"\theta=180^{\circ}-\gamma")
        + line(r"\theta=180^{\circ}-120^{\circ}=60^{\circ}")
    )


def _cube(m):
    a, b, c = m.helper
    return (
        "<p>Каждая грань куба — квадрат. Диагонали этих квадратов равны. Если ребро куба равно a, то по теореме Пифагора:</p>"
        + line("d^2=a^2+a^2")
        + line(r"d=a\sqrt{2}")
        + line(a + b + "=" + b + c + "=" + c + a + "=d")
        + "<p>Следовательно, треугольник "
        + _math(a + b + c)
        + " равносторонний. Все три угла равны, а их сумма равна 180°:</p>"
        + line(r"\theta+\theta+\theta=180^{\circ}")
        + line(r"3\theta=180^{\circ}")
        + line(r"\theta=60^{\circ}")
    )


def _face(m):
    bottom, top, upper = m.helper
    vertical = next(
        line_
        for line_ in m.requested
        if g.names(line_, 2)[0][0] == g.names(line_, 2)[1][0]
    )
    diagonal = next(line_ for line_ in m.requested if line_ != vertical)
    return (
        "<p>Боковые рёбра призмы параллельны. Перенесём прямую "
        + _math(vertical)
        + " к концу диагонали "
        + _math(diagonal)
        + ":</p>"
        + line(vertical + r"\parallel " + bottom + top)
        + line("a=" + value(m.edge))
        + "<p>Боковая грань — квадрат. Его диагональ делит прямоугольный равнобедренный треугольник на два равных острых угла:</p>"
        + line(bottom + top + "=" + top + upper + "=a")
        + line(r"\theta=\varphi")
        + line(r"\theta+\varphi=90^{\circ}")
        + line(r"2\theta=90^{\circ}")
        + line(r"\theta=45^{\circ}")
    )


def _center(m):
    a, b = m.helper
    return (
        "<p>Правильная четырёхугольная призма — прямоугольный параллелепипед. Все его диагонали равны. Обозначим сторону основания через a, диагональ через d, точку пересечения диагоналей через G:</p>"
        + line("d=2a")
        + "<p>В прямоугольном треугольнике катет равен половине гипотенузы, поэтому угол между диагональю и стороной основания имеет косинус 1/2. Оба угла при основании треугольника "
        + _math(a + "G" + b)
        + " равны 60°:</p>"
        + line(r"\cos\alpha=\frac{a}{d}")
        + line(r"\cos\alpha=\frac{a}{2a}=\frac{1}{2}")
        + line(r"\alpha=\beta=60^{\circ}")
        + "<p>По сумме углов треугольника найдём угол при точке пересечения диагоналей:</p>"
        + line(r"\theta=180^{\circ}-\alpha-\beta")
        + line(r"\theta=180^{\circ}-60^{\circ}-60^{\circ}=60^{\circ}")
        + "<p><b>Примечание.</b> Углом между прямыми называется меньший из углов, образованных при их пересечении.</p>"
    )


def _right(m):
    foot, far = m.helper
    vertex = m.requested[1]
    chord, vertical = far + foot, foot + vertex
    angle = "".join(m.requested)
    short = g.squared(m.points, chord) == 3
    chord_steps = (
        line(chord + r"^2=a^2+a^2-2a^2\cos120^{\circ}=3a^2")
        + line(chord + r"=a\sqrt{3}")
        if short
        else line(chord + "=2a") + line(chord + r"=2\cdot" + bracket(m.edge))
    )
    return (
        "<p>Рассмотрим прямоугольный треугольник "
        + _math(vertex + foot + far)
        + ". Его вертикальный катет — боковое ребро, равное стороне основания:</p>"
        + line("a=" + value(m.edge))
        + line(vertical + "=a")
        + "<p>Найдём катет в основании. "
        + (
            "По теореме косинусов, поскольку внутренний угол правильного шестиугольника равен 120°:"
            if short
            else "Большая диагональ правильного шестиугольника равна удвоенной стороне:"
        )
        + "</p>"
        + chord_steps
        + "<p>Тангенс острого угла равен отношению противолежащего катета к прилежащему:</p>"
        + line(r"\tg\angle " + angle + r"=\frac{" + chord + "}{" + vertical + "}")
        + line(
            r"\tg\angle "
            + angle
            + r"=\frac{"
            + bracket(sp.simplify(m.edge * (sp.sqrt(3) if short else 2)))
            + "}{"
            + bracket(m.edge)
            + "}="
            + value(m.tangent)
        )
        + (
            line(r"\angle " + angle + "=" + value(m.answer) + r"^{\circ}")
            if m.kind == "metric_vertex_angle"
            else ""
        )
    )


METHODS = {
    "chord_distance": _chord,
    "right_distance": _distance,
    "hexagon_bisector": _bisector,
    "hexagon_parallel": _parallel,
    "cube_equilateral": _cube,
    "square_face": _face,
    "center_equilateral": _center,
    "right_vertex": _right,
}


def render(m):
    return METHODS[m.method](m)
