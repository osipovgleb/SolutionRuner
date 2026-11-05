"""Coplanarity and the two ordered applications of Menelaus' theorem."""

from sympy import latex as value

from ..probability.common import line
from .spatial_distance_proofs import parts
from .spatial_metric_proofs import picture


def _concurrent(m):
    _, ab, sc, sa, bc, _request = m.names
    return (
        "<p>Прямые NL и MK пересекаются, поэтому лежат в одной плоскости. Следовательно, точки K, L, M и N компланарны. Прямая "
        + sa
        + ab
        + " — линия пересечения этой плоскости с SAB.</p>"
        + "<p>Она не параллельна SB: иначе через середину "
        + ab
        + " ребра AB проходила бы средняя линия треугольника SAB и точка "
        + sa
        + " была бы серединой SA. Это противоречит данному отношению:</p>"
        + line(r"\frac{A" + sa + "}{" + sa + "S}=" + value(m.q["ratio"]))
        + "<p>Пусть F — пересечение "
        + sa
        + ab
        + " и BS. Эта точка принадлежит плоскости сечения. Прямая "
        + sc
        + bc
        + " является её линией пересечения с SBC и также проходит через F. Поэтому все три указанные прямые пересекаются в F.</p>"
    )


def _menelaus(m):
    _, ab, sc, sa, bc, request = m.names
    first = (
        "<p>Рассмотрим треугольник SAB и секущую "
        + ab
        + sa
        + "F. По теореме Менелая:</p>"
        + line(
            r"\frac{BF}{FS}\cdot\frac{S"
            + sa
            + "}{"
            + sa
            + r"A}\cdot\frac{A"
            + ab
            + "}{"
            + ab
            + "B}=1"
        )
        + line(
            r"\frac{BF}{FS}=\frac{A"
            + sa
            + "}{"
            + sa
            + r"S}\cdot\frac{"
            + ab
            + "B}{A"
            + ab
            + "}="
            + value(m.q["ratio"])
        )
    )
    second = (
        "<p>В треугольнике SBC применим теорему Менелая к секущей "
        + sc
        + bc
        + "F:</p>"
        + line(
            r"\frac{C"
            + bc
            + "}{"
            + bc
            + r"B}\cdot\frac{BF}{FS}\cdot\frac{S"
            + sc
            + "}{"
            + sc
            + "C}=1"
        )
    )
    target = (
        (r"\frac{C" + bc + "}{" + bc + "B}")
        if request == "CN/NB"
        else (r"\frac{B" + bc + "}{" + bc + "C}")
    )
    calculation = (
        target
        + r"=\frac{FS}{BF}\cdot\frac{"
        + sc
        + "C}{S"
        + sc
        + "}="
        + value(m.answer)
        if request == "CN/NB"
        else target
        + r"=\frac{BF}{FS}\cdot\frac{S"
        + sc
        + "}{"
        + sc
        + "C}="
        + value(m.answer)
    )
    return first + second + line(calculation)


def _external(m):
    first = (
        "<p>Рассмотрим плоскость RML. Точка N лежит на RM, а K — на RL, поэтому M, N, K и L компланарны. Предположим, что MK ∥ NL. Тогда треугольники RMK и RNL подобны по двум углам, откуда:</p>"
        + line(r"\frac{RM}{RN}=\frac{RK}{RL}")
        + "<p>Но RN &lt; RM и RK &lt; RL: левая дробь больше 1, правая — меньше 1. Получено противоречие. Значит, компланарные прямые MK и NL не параллельны и пересекаются.</p>"
    )
    second = (
        "<p>В треугольнике SBC по теореме Менелая для секущей RL:</p>"
        + line(r"\frac{BL}{LC}\cdot\frac{CK}{KS}\cdot\frac{SR}{RB}=1")
        + line(
            r"\frac{SR}{RB}=\frac{LC}{BL}\cdot\frac{KS}{CK}=" + value(m.q["inverse"])
        )
        + "<p>Теперь применим теорему Менелая в SAB к секущей RM:</p>"
        + line(r"\frac{AN}{NS}\cdot\frac{SR}{RB}\cdot\frac{BM}{MA}=1")
        + line(r"\frac{AN}{NS}=\frac{RB}{SR}\cdot\frac{MA}{BM}=" + value(m.answer))
    )
    return first, second


def render(m, pictures):
    first, second = (
        _external(m) if m.names[0] == "external" else (_concurrent(m), _menelaus(m))
    )
    return picture(pictures) + parts(first, second)
