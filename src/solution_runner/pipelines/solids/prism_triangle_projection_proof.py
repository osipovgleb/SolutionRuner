"""Keep the parent's perpendicular projection for both triangular prism bases."""

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value
from .spatial_distance_proofs import parts


def _altitude(m):
    q = m.q
    return line(
        r"A_1M=\sqrt{A_1B_1^2-B_1M^2}=\sqrt{"
        + bracket(q["a"])
        + "^2-"
        + bracket(q["half_base"])
        + "^2}="
        + value(q["base_height"])
    )


def _isosceles_claim(m):
    proof = "<p>Пусть M — середина B₁C₁. В равнобедренном треугольнике A₁B₁C₁ медиана A₁M является высотой. Призма прямая, поэтому A₁M перпендикулярна также вертикальному направлению. Следовательно, A₁M перпендикулярна плоскости BCC₁.</p>"
    if m.symbols["claim"] != "square":
        return (
            proof
            + "<p>Плоскость BA₁M содержит прямую A₁M, перпендикулярную плоскости BCC₁. По признаку перпендикулярности плоскостей BA₁M ⟂ BCC₁.</p>"
        )
    return (
        proof
        + "<p>Пусть L — середина BC. Сечение плоскостью AA₁M — прямоугольник AA₁ML: AA₁ и LM — параллельные боковые рёбра, AL и A₁M — параллельные высоты оснований. Эта плоскость содержит A₁M и потому перпендикулярна BCC₁. Проверим равенство соседних сторон сечения:</p>"
        + line(r"B_1M=\frac{BC}{2}=" + value(m.q["half_base"]))
        + _altitude(m)
        + line(r"AA_1=" + value(m.q["height"]) + r"=A_1M")
        + "<p>Прямоугольник с равными соседними сторонами — квадрат. Утверждение доказано.</p>"
    )


def _isosceles_calculation(m):
    q = m.q
    return (
        "<p>Прямая BM — проекция A₁B на плоскость BCC₁. Значит, искомый угол равен A₁BM. По теореме Пифагора в прямоугольном треугольнике BB₁M:</p>"
        + line(r"B_1M=\frac{BC}{2}=" + value(q["half_base"]))
        + line(
            r"BM=\sqrt{BB_1^2+B_1M^2}=\sqrt{"
            + bracket(q["height"])
            + "^2+"
            + bracket(q["half_base"])
            + "^2}="
            + value(q["projection"])
        )
        + (_altitude(m) if m.symbols["claim"] != "square" else "")
        + "<p>В прямоугольном треугольнике A₁BM:</p>"
        + line(
            r"\tan\angle A_1BM=\frac{A_1M}{BM}=\frac{"
            + bracket(q["base_height"])
            + "}{"
            + bracket(q["projection"])
            + "}="
            + value(q["tan"])
        )
    )


def _right(m):
    q = m.q
    claim = "<p>По условию C₁H — высота треугольника A₁B₁C₁, поэтому C₁H ⟂ A₁B₁. Призма прямая, значит, C₁H перпендикулярна и прямой через H, параллельной AA₁. Эти две пересекающиеся прямые лежат в грани ABB₁A₁. Следовательно, C₁H перпендикулярна этой грани, а прямая BH — проекция C₁B на плоскость ABB₁.</p>"
    calculation = (
        "<p>Искомый угол равен C₁BH. Найдём высоту C₁H через площадь прямоугольного треугольника A₁B₁C₁:</p>"
        + line(
            r"A_1C_1=\sqrt{A_1B_1^2-B_1C_1^2}=\sqrt{"
            + bracket(q["hyp"])
            + "^2-"
            + bracket(q["leg"])
            + "^2}="
            + value(q["other"])
        )
        + line(
            r"C_1H=\frac{A_1C_1\cdot B_1C_1}{A_1B_1}=\frac{"
            + bracket(q["other"])
            + r"\cdot "
            + bracket(q["leg"])
            + "}{"
            + bracket(q["hyp"])
            + "}="
            + value(q["altitude"])
        )
        + line(
            r"BC_1=\sqrt{BB_1^2+B_1C_1^2}=\sqrt{"
            + bracket(q["height"])
            + "^2+"
            + bracket(q["leg"])
            + "^2}="
            + value(q["diagonal"])
        )
        + "<p>Рассмотрим прямоугольный треугольник C₁BH:</p>"
        + line(
            r"\sin\angle C_1BH=\frac{C_1H}{BC_1}=\frac{"
            + bracket(q["altitude"])
            + "}{"
            + bracket(q["diagonal"])
            + "}="
            + value(q["sine"])
        )
    )
    return claim, calculation


def render(m, pictures):
    claim, calculation = (
        _right(m)
        if m.symbols["base"] == "right"
        else (_isosceles_claim(m), _isosceles_calculation(m))
    )
    return parts(
        pictures.get("image_1", "") + claim,
        pictures.get("image_2", "") + calculation,
    )
