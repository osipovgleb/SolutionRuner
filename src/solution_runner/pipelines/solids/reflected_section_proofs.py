"""Use the true medians of the reflected-apex triangle to construct the section."""

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value
from .spatial_distance_proofs import parts
from .spatial_metric_proofs import picture


def _triangle(m):
    q = m.q
    return (
        "<p>Пусть B₁ — середина CD. В треугольнике SS₁B точки O и M — середины SS₁ и SB, поэтому BO и S₁M — медианы. Обозначим их пересечение через T. В основании BCD точка O — центр равностороннего треугольника:</p>"
        + line(r"\frac{BT}{TO}=2")
        + line(r"BO=\frac{2}{3}BB_1")
        + line(r"BT=\frac{2}{3}BO=\frac{4}{9}BB_1")
        + line(r"TB_1=BB_1-BT=\frac{5}{9}BB_1")
        + "<p>Из заданного положения L:</p>"
        + line(
            r"DL=\frac{2}{9}CD=\frac{2}{9}\cdot "
            + bracket(q["a"])
            + "="
            + value(2 * q["a"] / 9)
        )
        + line(r"LB_1=\frac{CD}{2}-DL=\frac{5}{18}CD")
        + line(r"\frac{B_1T}{B_1B}=\frac{B_1L}{B_1D}=\frac{5}{9}")
        + "<p>В треугольнике B₁BD по обратной теореме Фалеса TL ∥ BD. Пусть P — пересечение TL и BC. Через M проведём MK ∥ BD до пересечения с SD; K — середина SD. Получим сечение PMKL. По подобию треугольников CPL и CBD имеем BP = DL. Кроме того, BM = DK, а углы MBP и KDL равны как углы равносторонних граней. Поэтому треугольники BMP и DKL равны, MP = KL, и сечение — "
        + m.names[0]
        + " трапеция.</p>"
    )


def _square(m):
    return (
        "<p>В треугольнике ASS₁ точки O и M — середины SS₁ и AS. Поэтому AO и S₁M — медианы, а их пересечение T — центр тяжести:</p>"
        + line(r"\frac{AT}{TO}=2")
        + line(r"AO=\frac{AC}{2}")
        + line(r"AT=\frac{2}{3}AO=\frac{AC}{3}")
        + line(r"\frac{CT}{CA}=\frac{CL}{CB}=\frac{2}{3}")
        + "<p>В треугольнике CAB по обратной теореме Фалеса TL ∥ AB. Обозначим пересечение TL и AD через P. Тогда AP = BL. Через M проведём MK ∥ AB до пересечения с SB; K — середина SB. Четырёхугольник PMKL — искомое сечение.</p><p>Имеем AP = BL, AM = BK. Углы MAP и KBL равны как углы равносторонних боковых граней. Треугольники APM и BLK равны, поэтому PM = KL. Следовательно, сечение — "
        + m.names[0]
        + " трапеция.</p>"
    )


def render(m, pictures):
    q = m.q
    square = m.mode == "reflected_square_section_midline"
    first = _square(m) if square else _triangle(m)
    second = (
        "<p>Найдём основания трапеции. "
        + (
            "PL равно стороне квадратного основания:"
            if square
            else "В основании PL ∥ BD, поэтому треугольник CPL равносторонний и PL = CL:"
        )
        + "</p>"
        + line("PL=" + ("AB=" if square else r"CL=\frac{7}{9}CD=") + value(q["lower"]))
        + "<p>MK — средняя линия боковой грани:</p>"
        + line(
            r"MK=\frac{"
            + ("AB" if square else "BD")
            + r"}{2}=\frac{"
            + value(q["a"])
            + "}{2}="
            + value(q["upper"])
        )
        + "<p>Длина средней линии трапеции равна полусумме её оснований:</p>"
        + line(r"l=\frac{PL+MK}{2}")
        + line(
            r"l=\frac{"
            + value(q["lower"])
            + "+"
            + value(q["upper"])
            + "}{2}="
            + value(m.answer)
        )
    )
    return picture(pictures) + parts(first, second)
