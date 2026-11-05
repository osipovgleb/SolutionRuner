"""Explain base-area volume relations and the actual named triangular apothem."""

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value


def _product(*values):
    return r"\cdot".join(bracket(v) for v in values)


def base(m):
    q = m.q
    target = (
        "H" if m.kind.endswith("height") else "B" if m.kind == "center_area" else "V"
    )
    rows = ""
    if m.kind.startswith("center_"):
        rows = (
            "<p>В основании правильной треугольной пирамиды лежит равносторонний треугольник. Точка "
            + m.names[0]
            + " пересечения медиан является центром основания, поэтому "
            + m.names[1]
            + " — высота пирамиды.</p>"
        )
    if m.kind.startswith("rectangle_"):
        rows += (
            "<p>Основание пирамиды — прямоугольник. Найдём его площадь:</p>"
            + line("B=ab")
            + line("B=" + _product(q["a"], q["b"]) + "=" + value(q["B"]))
        )
    elif m.kind.startswith("triangle_"):
        rows += (
            "<p>Основание пирамиды — равносторонний треугольник. Его площадь равна:</p>"
            + line(r"B=\frac{\sqrt{3}}{4}a^2")
            + line(
                r"B=\frac{\sqrt{3}}{4}\cdot" + bracket(q["a"]) + "^2=" + value(q["B"])
            )
        )
    else:
        if target == "H":
            rows += line("B=" + value(q["B"])) + line("V=" + value(q["V"]))
        elif target == "V":
            rows += line("B=" + value(q["B"])) + line("H=" + value(q["H"]))
        else:
            rows += line("V=" + value(q["V"])) + line("H=" + value(q["H"]))
    rows += (
        "<p>Объём пирамиды равен трети произведения площади основания на высоту:</p>"
        + line(r"V=\frac{1}{3}BH")
    )
    if target == "H":
        return (
            rows
            + line(r"H=\frac{3V}{B}")
            + line(
                r"H=\frac{3\cdot"
                + bracket(q["V"])
                + "}{"
                + bracket(q["B"])
                + "}="
                + value(q["H"])
            )
        )
    if target == "B":
        return (
            rows
            + line(r"B=\frac{3V}{H}")
            + line(
                r"B=\frac{3\cdot"
                + bracket(q["V"])
                + "}{"
                + bracket(q["H"])
                + "}="
                + value(q["B"])
            )
        )
    return (
        rows
        + ("" if m.kind == "center_volume" else line("H=" + value(q["H"])))
        + line(r"V=\frac{1}{3}\cdot" + _product(q["B"], q["H"]))
        + line("V=" + value(q["V"]))
    )


def triangular_lateral(m):
    q = m.q
    mid, edge, side, slant = m.names
    opening = (
        "<p>Точка "
        + mid
        + " — середина ребра "
        + edge
        + ". В правильной пирамиде отрезок "
        + slant
        + " является апофемой боковой грани. Обозначим сторону основания a, апофему l, площадь боковой поверхности L:</p>"
    )
    rows = (
        opening
        + line("a=" + side)
        + line("l=" + slant)
        + line("P=3a")
        + "<p>Площадь боковой поверхности равна половине произведения периметра основания на апофему:</p>"
        + line(r"L=\frac{1}{2}Pl")
        + line(r"L=\frac{3}{2}al")
    )
    if m.kind == "triangle_lateral":
        return (
            rows
            + line(r"L=\frac{3}{2}\cdot" + _product(q["a"], q["l"]))
            + line("L=" + value(m.answer))
        )
    if m.kind == "triangle_apothem":
        return (
            rows
            + line(r"l=\frac{2L}{3a}")
            + line(
                r"l=\frac{2\cdot"
                + bracket(q["L"])
                + r"}{3\cdot"
                + bracket(q["a"])
                + "}="
                + value(m.answer)
            )
        )
    return (
        rows
        + line(r"a=\frac{2L}{3l}")
        + line(
            r"a=\frac{2\cdot"
            + bracket(q["L"])
            + r"}{3\cdot"
            + bracket(q["l"])
            + "}="
            + value(m.answer)
        )
    )


def floor(m):
    q = m.q
    shape = "квадратов" if q["x"] == q["y"] and q["u"] == q["v"] else "прямоугольников"
    return (
        "<p>Площадь многоугольника в основании равна разности площадей двух "
        + shape
        + ". По данным рисунка:</p>"
        + line("B=xy-uv")
        + line("B=" + _product(q["x"], q["y"]) + "-" + _product(q["u"], q["v"]))
        + line("B=" + value(q["B"]))
        + "<p>Указанное боковое ребро перпендикулярно основанию, поэтому его длина равна высоте пирамиды:</p>"
        + line("H=" + value(q["H"]))
        + line(r"V=\frac{1}{3}BH")
        + line(r"V=\frac{1}{3}\cdot" + _product(q["B"], q["H"]) + "=" + value(m.answer))
    )
