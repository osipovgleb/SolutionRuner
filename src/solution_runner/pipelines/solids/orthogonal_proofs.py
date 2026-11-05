"""Keep the parent's addition or subtraction of geometrically verified box volumes."""

from ..core.errors import ContentPlanError
from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value


def render(m, orders):
    if len(orders) != len(m.parts) or any(
        sorted(order) != [0, 1, 2] for order in orders
    ):
        raise ContentPlanError(
            "each parent box needs one explicit ordering of its three dimensions"
        )
    opening = (
        "Объём данного многогранника равен разности объёмов прямоугольного параллелепипеда и вырезанной части."
        if m.method == "subtract"
        else "Объём данного многогранника равен сумме объёмов составляющих его прямоугольных параллелепипедов."
    )
    rows = (
        "<p>"
        + opening
        + " Объём прямоугольного параллелепипеда равен произведению трёх его измерений:</p>"
        + line("V_1=a_1b_1c_1")
    )
    if m.differences:
        rows += (
            "<p>Найдём недостающие размеры как разности отмеченных на рисунке длин:</p>"
        )
        for i, (a, b) in enumerate(m.differences, 1):
            rows += line(
                "d_" + str(i) + "=" + value(a) + "-" + value(b) + "=" + value(a - b)
            )
    rows += "<p>Подставим размеры каждой части в формулу объёма:</p>"
    volumes = []
    for i, (part, order) in enumerate(zip(m.parts, orders), 1):
        dimensions = tuple(part.dimensions[j] for j in order)
        product = r"\cdot".join(bracket(d) for d in dimensions)
        rows += line("V_" + str(i) + "=" + product + "=" + value(part.volume))
        volumes.append(part.volume)
    operation = "-" if m.method == "subtract" else "+"
    rows += (
        "<p>"
        + (
            "Вычтем объём вырезанной части:"
            if m.method == "subtract"
            else "Сложим объёмы частей:"
        )
        + "</p>"
    )
    return (
        rows
        + line("V=" + operation.join("V_" + str(i) for i in range(1, len(m.parts) + 1)))
        + line("V=" + operation.join(value(v) for v in volumes) + "=" + value(m.answer))
    )
