"""Explain cone dimensions using the parents' right-triangle methods."""

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value


def _pythagoras(m, name):
    r, h, l = m.radius, m.height, m.slant
    formula, expression, result = {
        "r": ("r^2=l^2-h^2", bracket(l) + "^2-" + bracket(h) + "^2", r),
        "h": ("h^2=l^2-r^2", bracket(l) + "^2-" + bracket(r) + "^2", h),
        "l": ("l^2=h^2+r^2", bracket(h) + "^2+" + bracket(r) + "^2", l),
    }[name]
    return (
        line(formula)
        + line(name + r"=\sqrt{" + expression + "}")
        + line(name + "=" + value(result))
    )


def _right(m):
    return (
        "<p>Радиус основания, высота и образующая конуса образуют прямоугольный треугольник. Применим теорему Пифагора:</p>"
        + _pythagoras(m, "r" if m.input_kind == "height_slant" else "l")
    )


def _diameter(m):
    d = m.given[1] if m.input_kind == "height_diameter" else m.given[0]
    rows = (
        "<p>Рассмотрим осевое сечение конуса. Радиус равен половине диаметра основания:</p>"
        + line(r"r=\frac{d}{2}")
        + line(r"r=\frac{" + value(d) + "}{2}=" + value(m.radius))
    )
    if m.input_kind == "height_diameter":
        return (
            rows + "<p>Найдём образующую по теореме Пифагора:</p>" + _pythagoras(m, "l")
        )
    return rows + "<p>Найдём высоту по теореме Пифагора:</p>" + _pythagoras(m, "h")


def _base(m):
    return (
        "<p>Найдём радиус основания из площади круга:</p>"
        + line(r"B=\pi r^2")
        + line(r"r=\sqrt{\frac{B}{\pi}}")
        + line(r"r=\sqrt{\frac{" + value(m.given[0]) + r"}{\pi}}=" + value(m.radius))
    )


def _angle(m):
    r, h, l = m.radius, m.height, m.slant
    return (
        "<p>Высота конуса — катет напротив угла 30°, поэтому она равна половине образующей:</p>"
        + line(r"h=\frac{l}{2}")
        + line(r"h=\frac{" + value(l) + "}{2}=" + value(h))
        + "<p>Найдём радиус основания по теореме Пифагора:</p>"
        + line("r^2=l^2-h^2")
        + line(r"r=\sqrt{" + bracket(l) + "^2-" + bracket(h) + "^2}=" + value(r))
    )


def _apex(m):
    return (
        "<p>Высота делит прямой угол при вершине осевого сечения пополам. Получается равнобедренный прямоугольный треугольник:</p>"
        + line(r"\alpha=\frac{90^\circ}{2}=45^\circ")
        + line(r"r=\frac{d}{2}=\frac{" + value(m.given[0]) + "}{2}=" + value(m.radius))
        + line("h=r=" + value(m.height))
    )


def _rotation(m):
    return (
        "<p>При вращении равнобедренного прямоугольного треугольника вокруг катета этот катет становится высотой конуса, а второй равный катет — радиусом основания:</p>"
        + line("h=" + value(m.height))
        + line("r=" + value(m.radius))
    )


METHODS = {
    "height_slant": _right,
    "radius_height": _right,
    "height_diameter": _diameter,
    "diameter_slant": _diameter,
    "base_height": _base,
    "slant_angle": _angle,
    "diameter_apex": _apex,
    "rotation": _rotation,
}


def dimensions(m):
    return METHODS[m.input_kind](m)
