"""Keep the parent's altitude and parallel-line distance for the rectangle."""

import sympy as sp

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value
from .spatial_distance_proofs import parts


def _claim():
    return "<p>По условию AP : PB = CK : KB и AB = BC, поэтому BP = BK. Треугольники PBK и ABC подобны, следовательно, PK ∥ AC. Плоскость ω пересекает грань ASC по прямой ML, параллельной PK, где M лежит на SA, L — на SC. Поскольку ω ∥ SB, прямые MP и LK параллельны SB. Значит, LMPK — параллелограмм.</p><p>Пусть H — середина AC. В равнобедренных треугольниках SAC и BAC медианы SH и BH перпендикулярны AC. Следовательно, AC ⟂ SHB и, в частности, AC ⟂ SB. Поэтому LM ⟂ LK, а параллелограмм LMPK является прямоугольником.</p>"


def _dimensions(m):
    q = m.q
    return (
        line(r"AH=CH=\frac{AC}{2}=" + value(q["a"] / 2))
        + line(
            r"BH=\sqrt{BC^2-CH^2}=\sqrt{"
            + bracket(q["a"])
            + "^2-"
            + bracket(q["a"] / 2)
            + "^2}="
            + value(q["BH"])
        )
        + line(
            r"SH=\sqrt{SC^2-CH^2}=\sqrt{"
            + bracket(q["e"])
            + "^2-"
            + bracket(q["a"] / 2)
            + "^2}="
            + value(q["SH"])
        )
    )


def _altitude(m):
    q = m.q
    if q["BT"] == q["e"]:
        return (
            "<p>По найденным длинам BH² = SB² + SH². По теореме, обратной теореме Пифагора, SH ⟂ SB. Поэтому основание высоты T совпадает с S:</p>"
            + line(r"BT=SB=" + value(q["e"]))
            + line(r"HT=SH=" + value(q["SH"]))
        )
    right = sp.simplify(q["BH"] ** 2 - q["SH"] ** 2 + q["e"] ** 2)
    return (
        (
            "<p>Проведём высоту HT треугольника SHB. Положим BT = x, тогда ST = SB − x. Приравняем выражения для квадрата HT из двух прямоугольных треугольников:</p>"
            if q["BT"] < q["e"]
            else "<p>Проведём высоту HT треугольника SHB. Положим BT = x. Точка T лежит на продолжении SB за S, поэтому ST = x − SB. Приравняем выражения для квадрата HT из двух прямоугольных треугольников:</p>"
        )
        + line(r"HT^2=BH^2-BT^2=SH^2-ST^2")
        + line(
            bracket(q["BH"])
            + "^2-x^2="
            + bracket(q["SH"])
            + r"^2-\left("
            + value(q["e"])
            + r"-x\right)^2"
        )
        + line(value(2 * q["e"]) + "x=" + value(right))
        + line("x=" + value(q["BT"]))
        + line(
            r"HT=\sqrt{BH^2-BT^2}=\sqrt{"
            + bracket(q["BH"])
            + "^2-"
            + bracket(q["BT"])
            + "^2}="
            + value(q["HT"])
        )
    )


def _distance(m):
    q = m.q
    return (
        "<p>Пусть плоскость SHB пересекает ω по прямой QR, где Q лежит на SH, R — на BH. Тогда QR ∥ SB. Высота HT перпендикулярна как QR, так и направлению AC, поэтому она перпендикулярна ω. Искомое расстояние равно расстоянию между параллельными прямыми SB и QR.</p>"
        + _dimensions(m)
        + _altitude(m)
        + "<p>Из подобия треугольников BPK и BAC следует, что BR : RH = BK : KC. Параллельные прямые SB и QR делят высоту HT в том же отношении, считая от T. Поэтому расстояние от S до ω равно:</p>"
        + line(r"\frac{BR}{RH}=\frac{BK}{KC}=" + value(1 / q["ratio"]))
        + line(
            r"d(S,\omega)=\frac{BR}{BH}HT="
            + bracket(q["fraction"])
            + r"\cdot "
            + bracket(q["HT"])
            + "="
            + value(m.answer)
        )
    )


def render(m, pictures):
    return parts(pictures.get("image_1", "") + _claim(), _distance(m))
