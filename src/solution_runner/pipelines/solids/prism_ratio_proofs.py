"""Preserve the parents' similar-base, common-height and pyramid subtraction methods."""

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value


def _transfer(m):
    h = m.given[0]
    q = m.ratio
    return (
        "<p>Площадь правильного треугольника пропорциональна квадрату стороны. При переливании объём жидкости сохраняется:</p>"
        + line(r"B_1=\frac{\sqrt{3}}{4}a_1^2")
        + line(r"B_2=\frac{\sqrt{3}}{4}a_2^2")
        + line("a_2=" + bracket(q) + r"\cdot a_1")
        + line("V=B_1H_1=B_2H_2")
        + "<p>Выразим новую высоту, учитывая изменение площади основания:</p>"
        + line(r"H_2=H_1\left(\frac{a_1}{a_2}\right)^2")
        + line(r"H_2=\frac{H_1}{" + bracket(q) + "^2}")
        + line(r"H_2=\frac{" + value(h) + "}{" + bracket(q) + "^2}=" + value(m.answer))
    )


def _similar(m):
    return (
        "<p>Все рёбра меняются в одном отношении, поэтому призмы подобны. Коэффициент подобия равен:</p>"
        + line("k=" + value(m.ratio))
        + "<p>Площади поверхностей подобных тел относятся как квадрат коэффициента подобия:</p>"
        + line(r"\frac{S_1}{S_0}=k^2")
        + line("S_1=k^2S_0")
        + line("S_1=" + bracket(m.ratio) + r"^2\cdot" + bracket(m.given[0]))
        + line("S_1=" + value(m.answer))
    )


def _mid_volume(m):
    forward = m.kind == "mid_volume_part"
    final = (
        r"V_1=\frac{" + value(m.given[0]) + "}{4}=" + value(m.answer)
        if forward
        else r"V_0=4V_1=4\cdot" + bracket(m.given[0]) + "=" + value(m.answer)
    )
    return (
        "<p>Средняя линия отсекает треугольник, подобный исходному с коэффициентом 1/2. Площади оснований относятся как квадрат коэффициента подобия:</p>"
        + line(r"k=\frac{1}{2}")
        + line(r"B_1=k^2B_0=\frac{1}{4}B_0")
        + "<p>Плоскость параллельна боковому ребру, поэтому высоты призм одинаковы. Их объёмы относятся как площади оснований:</p>"
        + line("H_1=H_0")
        + line(r"\frac{V_1}{V_0}=\frac{B_1H_1}{B_0H_0}=\frac{1}{4}")
        + line(final)
    )


def _mid_lateral(m):
    forward = m.kind == "mid_lateral_part"
    final = (
        r"S_1=\frac{" + value(m.given[0]) + "}{2}=" + value(m.answer)
        if forward
        else r"S_0=2S_1=2\cdot" + bracket(m.given[0]) + "=" + value(m.answer)
    )
    return (
        "<p>Средняя линия уменьшает все стороны треугольного основания вдвое. Боковые рёбра и расстояние между основаниями не меняются:</p>"
        + line(r"k=\frac{1}{2}")
        + line("P_1=kP_0")
        + line("H_1=H_0")
        + "<p>Каждая соответствующая боковая грань имеет ту же высоту и вдвое меньшее основание, поэтому её площадь уменьшается вдвое. Для общей боковой поверхности получаем:</p>"
        + line("S_1=kS_0")
        + line(r"\frac{S_1}{S_0}=\frac{1}{2}")
        + line(final)
    )


def _remaining(m):
    return (
        "<p>Призма и отсечённая пирамида имеют одинаковые площадь основания и высоту:</p>"
        + line("V_0=BH")
        + line(r"V_p=\frac{1}{3}BH")
        + line(r"V_p=\frac{1}{3}V_0")
        + "<p>Вычтем объём отсечённой пирамиды, поскольку требуется оставшаяся часть:</p>"
        + line(r"V=V_0-V_p=\left(1-\frac{1}{3}\right)V_0")
        + line(r"V=\frac{2}{3}\cdot" + bracket(m.given[0]))
        + line("V=" + value(m.answer))
    )


def _corner(m):
    forward = m.kind == "cube_part"
    final = (
        r"V_1=\frac{" + value(m.given[0]) + "}{8}=" + value(m.answer)
        if forward
        else r"V_0=8V_1=8\cdot" + bracket(m.given[0]) + "=" + value(m.answer)
    )
    return (
        "<p>Диагональ делит квадратное основание куба на два равных треугольника. Сечение через середины рёбер отсекает треугольник с коэффициентом подобия 1/2:</p>"
        + line(r"k=\frac{1}{2}")
        + line(r"B_t=\frac{1}{2}B_0")
        + line(r"B_1=k^2B_t=\frac{1}{8}B_0")
        + "<p>Высота отсечённой призмы равна ребру куба, поэтому отношение объёмов равно отношению площадей оснований:</p>"
        + line("H_1=H_0")
        + line(r"\frac{V_1}{V_0}=\frac{B_1}{B_0}=\frac{1}{8}")
        + line(final)
    )


METHODS = {
    "transfer": _transfer,
    "similar_surface": _similar,
    "mid_volume_part": _mid_volume,
    "mid_volume_whole": _mid_volume,
    "mid_lateral_part": _mid_lateral,
    "mid_lateral_whole": _mid_lateral,
    "remove_pyramid": _remaining,
    "cube_part": _corner,
    "cube_whole": _corner,
}


def render(m):
    return METHODS[m.kind](m)
