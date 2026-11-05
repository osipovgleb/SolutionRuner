"""One section construction with volume, diagonal and perpendicular claims."""

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value
from .spatial_distance_proofs import parts
from .spatial_metric_proofs import picture


def _claim(m, x, y, foot):
    base = x + y
    if m.names[1] == "volume":
        return (
            "<p>Плоскость S"
            + base
            + " делит пирамиду на пирамиды SB"
            + y
            + x
            + " и S"
            + x
            + "ADC"
            + y
            + ". У них общая высота, проведённая из S, поэтому объёмы относятся как площади оснований. "
            + "Площадь прямоугольного треугольника B"
            + y
            + x
            + " равна половине от четверти площади квадрата:</p>"
            + line(
                "S_{B"
                + y
                + x
                + r"}=\frac{1}{2}\cdot\frac{AB}{2}\cdot\frac{BC}{2}=\frac{S_{ABCD}}{8}"
            )
            + line(
                "S_{"
                + x
                + "ADC"
                + y
                + r"}=S_{ABCD}-\frac{S_{ABCD}}{8}=\frac{7}{8} S_{ABCD}"
            )
            + line(
                r"\frac{V_{SB"
                + y
                + x
                + "}}{V_{S"
                + x
                + "ADC"
                + y
                + r"}}=\frac{\frac{1}{8}}{\frac{7}{8}}=\frac{1}{7}"
            )
        )
    if m.names[1] == "diagonal_ratio":
        return (
            "<p>Пусть O — центр квадрата, "
            + foot
            + " — пересечение "
            + base
            + " с DB. Отрезок "
            + base
            + " — средняя линия треугольника ABC, поэтому он параллелен AC и делит медиану BO пополам:</p>"
            + line("B" + foot + r"=\frac{BO}{2}=\frac{BD}{4}")
            + line("D" + foot + "=BD-B" + foot + r"=\frac{3}{4} BD")
            + line(
                r"\frac{D"
                + foot
                + "}{"
                + foot
                + r"B}=\frac{\frac{3}{4}}{\frac{1}{4}}=3"
            )
        )
    return (
        "<p>Пусть O — центр основания. Проекция SD на основание — прямая DO, лежащая на BD. "
        + base
        + " — средняя линия треугольника ABC, поэтому "
        + base
        + " ∥ AC. Диагонали квадрата перпендикулярны: AC ⟂ BD. Следовательно, "
        + base
        + " ⟂ DO, и по теореме о трёх перпендикулярах "
        + base
        + " ⟂ SD.</p>"
    )


def _area(m, x, y, foot):
    q = m.q
    base, left, right, height = x + y, "S" + x, "S" + y, "S" + foot
    equal = q["a"] == q["e"]
    reason = (
        "Боковые грани — равносторонние треугольники, так как все рёбра равны. "
        if equal
        else "Боковые грани — равнобедренные треугольники. "
    )
    return (
        "<p>Сечение — треугольник S"
        + base
        + ". Найдём последовательно "
        + left
        + ", "
        + base
        + " и "
        + right
        + ". "
        + reason
        + "Отрезки "
        + left
        + " и "
        + right
        + " — медианы этих граней, а значит, и их высоты:</p>"
        + line(left + "=" + right + r"=\sqrt{SA^2-\left(\frac{AB}{2}\right)^2}")
        + line(
            left
            + "="
            + right
            + r"=\sqrt{"
            + bracket(q["e"])
            + r"^2-\left(\frac{"
            + value(q["a"])
            + r"}{2}\right)^2}="
            + value(q["face_median"])
        )
        + "<p>В прямоугольном треугольнике "
        + x
        + "B"
        + y
        + " катеты равны половине стороны основания. По теореме Пифагора:</p>"
        + line(
            base + r"=\sqrt{\left(\frac{AB}{2}\right)^2+\left(\frac{BC}{2}\right)^2}"
        )
        + line(
            base
            + r"=\sqrt{2\cdot\left(\frac{"
            + value(q["a"])
            + r"}{2}\right)^2}="
            + value(q["section_base"])
        )
        + "<p>Проведём высоту "
        + height
        + " равнобедренного треугольника S"
        + base
        + ". Точка "
        + foot
        + " — середина "
        + base
        + ". По теореме Пифагора:</p>"
        + line(
            height + r"=\sqrt{" + left + r"^2-\left(\frac{" + base + r"}{2}\right)^2}"
        )
        + line(
            height
            + r"=\sqrt{"
            + bracket(q["face_median"])
            + r"^2-\left(\frac{"
            + value(q["section_base"])
            + r"}{2}\right)^2}="
            + value(q["section_height"])
        )
        + line("S_{S" + base + r"}=\frac{1}{2}\cdot " + base + r"\cdot " + height)
        + line(
            "S_{S"
            + base
            + r"}=\frac{1}{2}\cdot "
            + bracket(q["section_base"])
            + r"\cdot "
            + bracket(q["section_height"])
            + "="
            + value(m.answer)
        )
    )


def render(m, pictures):
    x = m.symbols.get("on_AB", "K")
    y = m.symbols.get("on_BC", "M")
    foot = m.symbols.get("height_foot", "P")
    introduction = "<p>Пусть " + x + " — середина AB, а " + y + " — середина BC.</p>"
    return picture(pictures) + parts(
        introduction + _claim(m, x, y, foot), _area(m, x, y, foot)
    )
