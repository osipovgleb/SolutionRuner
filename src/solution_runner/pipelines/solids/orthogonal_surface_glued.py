"""Preserve contact subtraction, through-hole and central-cancellation parent methods."""

from itertools import combinations

from ..core.errors import ContentPlanError
from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value
from .orthogonal_surface_bbox import box_rows, product
from .orthogonal_surface_geometry import (
    bounding,
    central_cancellation,
    contact_dimensions,
    glued_parts,
    missing_box,
)


def area_row(name, box, order):
    a, b, c = (box.dimensions[i] for i in order)
    expression = "+".join(product(*p) for p in ((a, b), (a, c), (b, c)))
    return line(name + r"=2\left(" + expression + r"\right)=" + value(box.surface))


def glued(m, style):
    parts, shared = glued_parts(m, style["method"])
    orders = style["orders"]
    if len(orders) != len(parts) or any(sorted(order) != [0, 1, 2] for order in orders):
        raise ContentPlanError(
            "one reviewed dimension ordering is required for each surface part"
        )
    rows = (
        "<p>Разделим многогранник на прямоугольные параллелепипеды. Найдём площадь поверхности каждого по трём его измерениям:</p>"
        + line("S_1=2(a_1b_1+a_1c_1+b_1c_1)")
    )
    for i, (part, order) in enumerate(zip(parts, orders), 1):
        rows += area_row("S_" + str(i), part, order)
    terms = [
        product(*d)
        for a, b in combinations(parts, 2)
        if (d := contact_dimensions(a, b))
    ]
    rows += (
        "<p>Внутренние грани в сумму поверхностей частей вошли дважды. Вычтем две площади каждого общего участка:</p>"
        + line("A=" + "+".join(terms) + "=" + value(shared))
        + line("S=" + "+".join("S_" + str(i) for i in range(1, len(parts) + 1)) + "-2A")
        + line(
            "S="
            + "+".join(value(p.surface) for p in parts)
            + r"-2\cdot"
            + bracket(shared)
            + "="
            + value(m.solid.surface)
        )
    )
    return rows


def shelf_bbox(m):
    box = bounding(m)
    tall, side = m.solid.additions
    width, height = side.dimensions[0], side.dimensions[2]
    gap = tall.dimensions[2] - height
    removed = width * gap
    if box.surface - 2 * removed != m.solid.surface:
        raise ContentPlanError(
            "the total vertical gaps do not give the exposed surface"
        )
    return (
        "<p>Рассмотрим описывающий параллелепипед. Из его поверхности нужно вычесть четыре прямоугольника у верхнего и нижнего выступов:</p>"
        + box_rows(box)
        + "<p>Отдельные высоты промежутков не отмечены. Их сумма G равна разности общей высоты и высоты бокового выступа; этого достаточно для вычисления общей вычитаемой площади:</p>"
        + line(
            "G=" + value(tall.dimensions[2]) + "-" + value(height) + "=" + value(gap)
        )
        + line("B=" + product(width, gap) + "=" + value(removed))
        + line("S=S_0-2B")
        + line(
            "S="
            + value(box.surface)
            + r"-2\cdot"
            + bracket(removed)
            + "="
            + value(m.solid.surface)
        )
    )


def hole(m):
    box, cut = bounding(m), missing_box(m)
    w, _d, h = cut.dimensions
    front = w * h
    if box.surface + cut.surface - 4 * front != m.solid.surface:
        raise ContentPlanError(
            "the through-hole face identity does not match the boundary"
        )
    return (
        "<p>Сложим поверхности большого параллелепипеда и маленького параллелепипеда, соответствующего отверстию:</p>"
        + box_rows(box)
        + line("S_1=2(wd+wh+dh)")
        + area_row("S_1", cut, (0, 1, 2))
        + "<p>Два основания отверстия из внешних граней исчезли. Кроме того, они лишний раз вошли в поверхность малого параллелепипеда. Поэтому вычтем четыре площади передней грани отверстия:</p>"
        + line("B=" + product(w, h) + "=" + value(front))
        + line("S=S_0+S_1-4B")
        + line(
            "S="
            + value(box.surface)
            + "+"
            + value(cut.surface)
            + r"-4\cdot"
            + bracket(front)
            + "="
            + value(m.solid.surface)
        )
    )


def hole_faces(m):
    box, cut = bounding(m), missing_box(m)
    a, b, c = box.dimensions
    w, _d, h = cut.dimensions
    values = (a * c - w * h, b * c, a * b, w * b, h * b)
    return (
        "<p>Посчитаем площадь передней грани за вычетом отверстия, боковой и нижней внешних граней. Задняя, противоположная боковая и верхняя грани имеют те же площади:</p>"
        + line(
            "F=ac-wh=" + product(a, c) + "-" + product(w, h) + "=" + value(values[0])
        )
        + line("L=bc=" + product(b, c) + "=" + value(values[1]))
        + line("D=ab=" + product(a, b) + "=" + value(values[2]))
        + "<p>Учтём также нижнюю и боковую стенки сквозного отверстия. Их противоположные стенки равны им по площади:</p>"
        + line("Q=wb=" + product(w, b) + "=" + value(values[3]))
        + line("R=hb=" + product(h, b) + "=" + value(values[4]))
        + line("S=2(F+L+D+Q+R)")
        + line(
            r"S=2\left("
            + "+".join(value(v) for v in values)
            + r"\right)="
            + value(m.solid.surface)
        )
    )


def cancelled(m, style):
    central, parts, shared = central_cancellation(m)
    rows = (
        "<p>Рассмотрим верхний, передний и левый выступы. Под верхним выступом находится центральный блок. Его поверхность в точности компенсируется удвоенной суммой трёх внутренних площадей соприкосновения:</p>"
        + line("S_c=2(ab+ac+bc)")
        + line("A=ab+ac+bc")
        + line("S_c-2A=0")
        + "<p>Поэтому остаётся сложить поверхности трёх выступов. Найдём каждую из них по измерениям на рисунке:</p>"
    )
    for i, (part, order) in enumerate(zip(parts, style["orders"]), 1):
        rows += area_row("S_" + str(i), part, order)
    if central.surface != 2 * shared:
        raise ContentPlanError("the central block contribution must vanish")
    return (
        rows
        + line("S=S_1+S_2+S_3")
        + line(
            "S="
            + "+".join(value(p.surface) for p in parts)
            + "="
            + value(m.solid.surface)
        )
    )
