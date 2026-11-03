"""Retain each parent's scalar method, including both diagonal-midpoint proofs."""

from ...probability.common import line
from ...triangles.right.altitude_methods import solution_section
from ..parallelogram.rectangle_proofs import value


def _angle(m):
    d = value(m.given[0])
    large, small = value(m.answer), value(180 - m.answer)
    return (
        "<p>В равнобедренной трапеции углы при каждом основании равны, а углы при боковой стороне в сумме дают 180°. Поэтому сумма противолежащих углов также равна 180°. Составим систему, обозначив больший угол через ∠C:</p>"
        + line(
            r"\begin{cases}\angle C-\angle A="
            + d
            + r"^{\circ}\\\angle C+\angle A=180^{\circ}\end{cases}"
        )
        + "<p>Сложим уравнения, найдём больший угол, затем выразим меньший:</p>"
        + line(
            r"2\angle C=180^{\circ}+"
            + d
            + r"^{\circ}="
            + value(180 + m.given[0])
            + r"^{\circ}"
        )
        + line(
            r"\angle C=\frac{"
            + value(180 + m.given[0])
            + "}{2}^{\\circ}="
            + large
            + r"^{\circ}"
        )
        + line(r"\angle A=180^{\circ}-" + large + r"^{\circ}=" + small + r"^{\circ}")
    )


def _large(m):
    median, small = map(value, m.given)
    return (
        "<p>Пусть длина большего основания равна x. Средняя линия равна полусумме длин оснований. Запишем это свойство и выразим x:</p>"
        + line(r"m=\frac{a+x}{2}")
        + line(small + "+x=2\\cdot " + median)
        + line("x=2\\cdot " + median + "-" + small)
        + line("x=" + value(2 * m.given[0]) + "-" + small + "=" + value(m.answer))
    )


def _piece(m):
    small, large = sorted(m.given)
    return (
        "<p>Обозначим основания так, что AD — большее, BC — меньшее. Пусть E и F — середины боковых сторон, а O — точка пересечения средней линии с диагональю BD. В треугольнике ABD отрезок EO — средняя линия, поэтому он равен половине AD:</p>"
        + line(r"EO=\frac{AD}{2}")
        + line(r"EO=\frac{" + value(large) + "}{2}=" + value(m.answer))
        + "<p>Второй отрезок — средняя линия треугольника BCD. Сравним его с EO:</p>"
        + line(r"OF=\frac{BC}{2}=\frac{" + value(small) + "}{2}=" + value(small / 2))
        + "<p>Так как AD больше BC, искомый больший отрезок — EO.</p>"
    )


def _cut(m):
    small, perimeter = m.given
    return (
        "<p>Заметим, что четырёхугольник EBCD — параллелограмм: EB параллельна CD по построению, а ED параллельна BC как часть основания. Его противоположные стороны попарно равны:</p>"
        + line("CD=BE")
        + line("ED=BC")
        + "<p>Выразим периметр трапеции через периметр отсечённого треугольника ABE и меньшее основание:</p>"
        + line(r"P_{ABCD}=AB+BC+CD+AD")
        + line(r"P_{ABCD}=AB+BC+BE+(AE+ED)")
        + line(r"P_{ABCD}=(AB+BE+AE)+2BC=P_{ABE}+2BC")
        + line(r"P_{ABCD}=" + value(perimeter) + r"+2\cdot " + value(small))
        + line(
            r"P_{ABCD}="
            + value(perimeter)
            + "+"
            + value(2 * small)
            + "="
            + value(m.answer)
        )
    )


def _parts(m):
    short, long = sorted(m.given)
    return (
        "<p>Пусть CE — проведённая высота, AE — большая часть основания, ED — меньшая. В равнобедренной трапеции проекции боковых сторон на большее основание равны, поэтому BC=AE−ED. Найдём среднюю линию:</p>"
        + line(
            "AD=AE+ED=" + value(long) + "+" + value(short) + "=" + value(long + short)
        )
        + line(
            "BC=AE-ED=" + value(long) + "-" + value(short) + "=" + value(long - short)
        )
        + line(r"m=\frac{AD+BC}{2}")
        + line(r"m=\frac{(AE+ED)+(AE-ED)}{2}=AE")
        + line("m=" + value(m.answer))
        + "<p><b>Примечание.</b></p><p>Высота из вершины тупого угла равнобедренной трапеции делит большее основание на два отрезка: больший равен полусумме оснований, то есть средней линии, а меньший — их полуразности.</p>"
    )


def _perimeter(m):
    perimeter, legs = map(value, m.given)
    return (
        "<p>Средняя линия EF равна полусумме оснований. Сумма оснований получается вычитанием суммы боковых сторон из периметра. Последовательно получаем:</p>"
        + line(r"EF=\frac{AD+BC}{2}")
        + line(r"AD+BC=P_{ABCD}-(AB+CD)")
        + line("AD+BC=" + perimeter + "-" + legs + "=" + value(m.given[0] - m.given[1]))
        + line(r"EF=\frac{P_{ABCD}-(AB+CD)}{2}")
        + line(r"EF=\frac{" + perimeter + "-" + legs + "}{2}=" + value(m.answer))
    )


def _midpoints(m, pictures):
    small, large = sorted(m.given)
    midline = (small + large) / 2
    first = (
        pictures["detail"]
        + "<p>Обозначим большее основание AD, меньшее BC. Пусть KM — средняя линия трапеции, а E и F — середины диагоналей. Отрезки EK и FM — средние линии треугольников ABC и DBC, поэтому:</p>"
        + line(r"EK=FM=\frac{BC}{2}=\frac{" + value(small) + "}{2}=" + value(small / 2))
        + "<p>Вычтем эти два отрезка из средней линии KM:</p>"
        + line(
            r"KM=\frac{BC+AD}{2}=\frac{"
            + value(small)
            + "+"
            + value(large)
            + "}{2}="
            + value(midline)
        )
        + line("EF=KM-EK-FM")
        + line(r"EF=\frac{BC+AD}{2}-BC")
        + line("EF=" + value(midline) + "-" + value(small) + "=" + value(m.answer))
    )
    second = (
        "<p>Отрезок, соединяющий середины диагоналей трапеции, равен полуразности длин большего и меньшего оснований. Следовательно:</p>"
        + line(r"EF=\frac{AD-BC}{2}")
        + line(r"EF=\frac{" + value(large) + "-" + value(small) + "}{2}")
        + line(r"EF=\frac{" + value(large - small) + "}{2}=" + value(m.answer))
    )
    return solution_section("Решение", first) + solution_section(
        "Приведём другое решение", second
    )


def _perpendicular(m):
    return (
        "<p>Пусть E и F — середины оснований AD и BC, O — точка пересечения диагоналей. Сначала используем свойство трапеции с перпендикулярными диагоналями: EF равно средней линии.</p>"
        + "<p>Обоснуем это свойство. Прямоугольные треугольники AOD и BOC имеют гипотенузы AD и BC. Их медианы, проведённые к гипотенузам, равны половинам этих оснований:</p>"
        + line(r"OE=\frac{AD}{2}")
        + line(r"OF=\frac{BC}{2}")
        + "<p>В равнобедренной трапеции середины оснований и точка пересечения диагоналей лежат на оси симметрии. Точка O лежит между E и F, поэтому:</p>"
        + line(r"EF=OE+OF=\frac{AD+BC}{2}")
        + "<p>Отрезок EF соединяет середины оснований равнобедренной трапеции и перпендикулярен им, значит, является её высотой. Средняя линия также равна полусумме оснований:</p>"
        + line(r"m=\frac{AD+BC}{2}=EF=h")
        + line("m=" + value(m.given[0]))
    )


def render(m, pictures):
    if m.mode == "diagonal_midpoints":
        return _midpoints(m, pictures)
    method = {
        "angle_difference": _angle,
        "large_base": _large,
        "diagonal_piece": _piece,
        "cut_perimeter": _cut,
        "base_parts": _parts,
        "perimeter_midline": _perimeter,
        "perpendicular": _perpendicular,
    }[m.mode]
    return solution_section("Решение", method(m))
