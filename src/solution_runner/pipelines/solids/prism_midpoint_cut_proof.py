"""Construct one midpoint trapezoid and calculate its requested quantity."""

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value
from .spatial_distance_proofs import parts
from .spatial_metric_proofs import picture


def names(m):
    construct = m.names[0] == "construct"
    end = m.names[1][1]
    opposite = "C" if end == "B" else "B"
    left, right = ("N", "K") if construct else ("M", "N")
    top = m.symbols["top"]
    return end, opposite, left, right, top


def _construction(m):
    end, opposite, left, right, top = names(m)
    base = "A" + end
    upper = left + right
    top_edge = "A" + top + end + top
    left_edge = "A" + top + opposite + top
    right_edge = end + top + opposite + top
    display = lambda s: s.replace("_1", "₁")
    text = (
        "<p>Через "
        + left
        + " проведём прямую, параллельную "
        + base
        + ", до пересечения с "
        + display(right_edge)
        + " в точке "
        + right
        + ". "
        + "Поскольку "
        + left
        + " — середина "
        + display(left_edge)
        + ", по теореме о средней линии треугольника "
        + display("A" + top + end + top + opposite + top)
        + " точка "
        + right
        + " — середина "
        + display(right_edge)
        + ", и:</p>"
        + line(upper + r"\parallel " + top_edge + r"\parallel " + base)
        + "<p>Прямые "
        + upper
        + " и "
        + base
        + " лежат в одной плоскости. Она пересекает призму по трапеции "
        + ("ABKN" if m.names[0] == "construct" else "A" + left + right + end)
        + ". "
        + "Её боковые стороны — гипотенузы прямоугольных треугольников с равными катетами: высотами призмы и половинами равных рёбер верхнего основания. Поэтому трапеция равнобедренная.</p>"
    )
    return text


def _bases(m):
    q = m.q
    end, _opposite, left, right, top = names(m)
    return line("A" + end + "=" + value(q["a"])) + line(
        left
        + right
        + r"=\frac{A"
        + top
        + end
        + top
        + r"}{2}=\frac{"
        + value(q["a"])
        + "}{2}="
        + value(q["upper"])
    )


def _side(m):
    q = m.q
    end, opposite, left, right, top = names(m)
    half = "A" + top + left
    height = "AA" + top
    side = "A" + left
    return (
        "<p>По теореме Пифагора найдём боковую сторону сечения в прямоугольном треугольнике "
        + ("AA" + top + left).replace("_1", "₁")
        + ":</p>"
        + line(
            half
            + r"=\frac{A"
            + top
            + opposite
            + top
            + r"}{2}=\frac{"
            + value(q["a"])
            + "}{2}="
            + value(q["upper"])
        )
        + line(
            side
            + r"=\sqrt{"
            + height
            + "^2+"
            + half
            + r"^2}=\sqrt{"
            + bracket(q["height"])
            + "^2+"
            + bracket(q["upper"])
            + "^2}="
            + value(q["side"])
        )
        + line(end + right + "=" + side + "=" + value(q["side"]))
    )


def _perimeter(m):
    q = m.q
    end, _opposite, left, right, _top = names(m)
    boundary = "ABKN" if m.names[0] == "construct" else "A" + left + right + end
    base, upper = "A" + end, left + right
    return (
        "<p>Сложим две боковые стороны и основания трапеции:</p>"
        + line(
            "P_{"
            + boundary
            + "}="
            + base
            + "+"
            + end
            + right
            + "+"
            + upper
            + "+"
            + left
            + "A"
        )
        + line(
            "P_{"
            + boundary
            + "}="
            + value(q["a"])
            + "+"
            + bracket(q["side"])
            + "+"
            + bracket(q["upper"])
            + "+"
            + bracket(q["side"])
            + "="
            + value(m.answer)
        )
    )


def _area(m):
    q = m.q
    end, _opposite, left, right, _top = names(m)
    boundary = "ABKN" if m.names[0] == "construct" else "A" + left + right + end
    base, upper = "A" + end, left + right
    return (
        "<p>Проведём высоту "
        + left
        + "H к основанию "
        + base
        + ". В равнобедренной трапеции AH равно половине разности оснований:</p>"
        + line(
            r"AH=\frac{"
            + base
            + "-"
            + upper
            + r"}{2}=\frac{"
            + value(q["a"])
            + "-"
            + bracket(q["upper"])
            + "}{2}="
            + value(q["offset"])
        )
        + line(
            left
            + r"H=\sqrt{A"
            + left
            + r"^2-AH^2}=\sqrt{"
            + bracket(q["side"])
            + "^2-"
            + bracket(q["offset"])
            + "^2}="
            + value(q["section_height"])
        )
        + line(
            "S_{"
            + boundary
            + r"}=\frac{"
            + base
            + "+"
            + upper
            + r"}{2}\cdot "
            + left
            + "H"
        )
        + line(
            "S_{"
            + boundary
            + r"}=\frac{"
            + value(q["a"])
            + "+"
            + bracket(q["upper"])
            + r"}{2}\cdot "
            + bracket(q["section_height"])
            + "="
            + value(m.answer)
        )
    )


def render(m, pictures):
    calculation = (
        _side(m) + _bases(m) if m.names[0] == "construct" else _bases(m) + _side(m)
    ) + (_perimeter(m) if m.mode.endswith("perimeter") else _area(m))
    content = (
        _construction(m) + calculation
        if m.names[0] == "construct"
        else parts(_construction(m), calculation)
    )
    return picture(pictures) + content
