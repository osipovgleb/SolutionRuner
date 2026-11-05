"""Keep bounding-box, projection and nine-face methods for stepped solids and corners."""

from ..core.errors import ContentPlanError
from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value
from .orthogonal_surface_geometry import bounding, corner, missing_box


def product(*xs):
    return r"\cdot".join(bracket(x) for x in xs)


def box_rows(box):
    a, b, c = box.dimensions
    pairs = ((a, b), (a, c), (b, c))
    return line("S_0=2(ab+ac+bc)") + line(
        "S_0=2"
        + r"\left("
        + "+".join(product(*p) for p in pairs)
        + r"\right)="
        + value(box.surface)
    )


def reduced(m, style):
    box, cut = bounding(m), missing_box(m)
    axes = {"reduced_xy": (0, 1), "reduced_xz": (0, 2), "reduced_yz": (1, 2)}[style]
    u, v = (cut.dimensions[i] for i in axes)
    area = u * v
    if box.surface - 2 * area != m.solid.surface:
        raise ContentPlanError(
            "the step face cancellation does not match the actual surface"
        )
    return (
        "<p>Дополним многогранник до прямоугольного параллелепипеда с измерениями a, b, c. Найдём площадь его поверхности:</p>"
        + box_rows(box)
        + "<p>При переходе к ступенчатому телу часть граней заменяется равными по площади. Остаётся вычесть две площади прямоугольника выреза:</p>"
        + line("B=" + product(u, v) + "=" + value(area))
        + line("S=S_0-2B")
        + line(
            "S="
            + value(box.surface)
            + r"-2\cdot"
            + bracket(area)
            + "="
            + value(m.solid.surface)
        )
    )


def unchanged(m):
    box, _cut = corner(m)
    x, y, z = box.dimensions
    products = (x * y, x * z, y * z)
    return (
        "<p>Три удалённых участка внешних граней заменяются равными им гранями выреза. Поэтому площадь поверхности сохраняется и равна площади поверхности описывающего параллелепипеда:</p>"
        + line("S_0=2(ab+ac+bc)")
        + line(
            r"S_0=2\left("
            + product(x, y)
            + "+"
            + product(x, z)
            + "+"
            + product(y, z)
            + r"\right)"
        )
        + "<p>Вычислим площади прямоугольников и сложим их:</p>"
        + line(r"S_0=2\left(" + "+".join(value(p) for p in products) + r"\right)")
        + line(r"S_0=2\cdot" + bracket(sum(products)))
        + line("S=S_0=" + value(m.solid.surface))
    )


def grouped(m):
    box, _cut = corner(m)
    x, y, z = box.dimensions
    h, b, f = 2 * x * y, 2 * y * z, 2 * x * z
    return (
        "<p>Найдём площадь как сумму площадей горизонтальных, боковых и фронтальных граней. Верхние участки вместе равны нижней грани; правые — левой, передние — задней:</p>"
        + line("H=2ab=2" + r"\cdot" + product(x, y) + "=" + value(h))
        + line("L=2bc=2" + r"\cdot" + product(y, z) + "=" + value(b))
        + line("F=2ac=2" + r"\cdot" + product(x, z) + "=" + value(f))
        + "<p>Сложим площади трёх групп граней:</p>"
        + line("S=H+L+F")
        + line(
            "S="
            + value(h)
            + "+"
            + value(b)
            + "+"
            + value(f)
            + "="
            + value(m.solid.surface)
        )
    )


def nine_faces(m):
    box, cut = corner(m)
    x, y, z = box.dimensions
    w, d, h = cut.dimensions
    full = (y * z, x * y, x * z)
    shortened = (x * z - w * h, y * z - d * h, x * y - w * d)
    added = (w * d, w * h, d * h)
    return (
        "<p>Проверим результат сложением площадей всех девяти граней. Обозначим размеры описывающего параллелепипеда через a, b, c, а размеры выреза — через w, d, h. Сначала учтём правую, нижнюю и заднюю грани:</p>"
        + line("A_1=bc+ab+ac")
        + line("A_1=" + "+".join(value(v) for v in full) + "=" + value(sum(full)))
        + "<p>Передняя, левая и верхняя внешние грани уменьшились на прямоугольники выреза. Затем учтём три новые малые грани:</p>"
        + line("A_2=(ac-wh)+(bc-dh)+(ab-wd)")
        + line(
            "A_2=" + "+".join(value(v) for v in shortened) + "=" + value(sum(shortened))
        )
        + line("A_3=wd+wh+dh")
        + line("A_3=" + "+".join(value(v) for v in added) + "=" + value(sum(added)))
        + "<p>Все девять граней учтены ровно один раз:</p>"
        + line("S=A_1+A_2+A_3")
        + line(
            "S="
            + "+".join(value(sum(v)) for v in (full, shortened, added))
            + "="
            + value(m.solid.surface)
        )
    )


def groove(m, style):
    box, cut = bounding(m), missing_box(m)
    x, _y, z = box.dimensions
    w, d, h = cut.dimensions
    u, v = (d, z) if style == "front_notch" else (d, x)
    p, q = (w, d) if style == "front_notch" else (d, h)
    added, removed = u * v, p * q
    if box.surface + 2 * added - 2 * removed != m.solid.surface:
        raise ContentPlanError("the groove identity differs from the exposed faces")
    return (
        "<p>Возьмём поверхность описывающего параллелепипеда. Часть противоположных граней выреза заменяет равные участки исходной поверхности:</p>"
        + box_rows(box)
        + "<p>Учтём две новые стенки и вычтем два исчезнувших прямоугольника:</p>"
        + line("A=" + product(u, v) + "=" + value(added))
        + line("B=" + product(p, q) + "=" + value(removed))
        + line("S=S_0+2A-2B")
        + line(
            "S="
            + value(box.surface)
            + r"+2\cdot"
            + bracket(added)
            + r"-2\cdot"
            + bracket(removed)
            + "="
            + value(m.solid.surface)
        )
    )
