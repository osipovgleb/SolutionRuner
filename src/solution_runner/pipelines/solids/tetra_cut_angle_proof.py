"""The parent volume comparison and three cosine-law calculations."""

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value
from .spatial_distance_proofs import parts


def _volumes(m, pictures):
    q = m.q
    upper, lower = ("CMKDB", "CMKA") if m.names[0] == "remaining" else ("CMKA", "CMKDB")
    first, second = (
        (q["remaining_coefficient"], q["corner_coefficient"])
        if m.names[0] == "remaining"
        else (q["corner_coefficient"], q["remaining_coefficient"])
    )
    return (
        pictures.get("image_1", "")
        + "<p>Пусть CO = h &gt; 0 — высота тетраэдра к грани ABD. Треугольник ABD равносторонний. Треугольник AMK также равносторонний: AM = AK, а угол MAK равен 60°. Обе пирамиды с вершиной C имеют одну высоту h:</p>"
        + line(r"V_{ABCD}=\frac{1}{3} hS_{ABD}=\frac{1}{3} h\cdot\frac{AB^2\sqrt3}{4}")
        + line(
            r"V_{ABCD}=\frac{"
            + bracket(q["a"])
            + r"^2\sqrt3}{12}h="
            + bracket(q["total_coefficient"])
            + "h"
        )
        + line(r"V_{CMKA}=\frac{1}{3} hS_{AMK}=\frac{1}{3} h\cdot\frac{AM^2\sqrt3}{4}")
        + line(
            r"V_{CMKA}=\frac{"
            + bracket(q["t"])
            + r"^2\sqrt3}{12}h="
            + bracket(q["corner_coefficient"])
            + "h"
        )
        + "<p>Остаток тетраэдра имеет объём:</p>"
        + line(
            r"V_{CMKDB}=V_{ABCD}-V_{CMKA}=("
            + value(q["total_coefficient"])
            + "-"
            + bracket(q["corner_coefficient"])
            + ")h="
            + bracket(q["remaining_coefficient"])
            + "h"
        )
        + line(
            r"\frac{V_{"
            + upper
            + r"}}{V_{"
            + lower
            + r"}}=\frac{"
            + bracket(first)
            + "h}{"
            + bracket(second)
            + r"h}=\frac{"
            + bracket(first)
            + "}{"
            + bracket(second)
            + r"}=\frac{"
            + value(q["p"])
            + "}{"
            + value(q["q"])
            + "}"
        )
    )


def _construction(m):
    q = m.q
    return (
        "<p>Пусть A₁ — середина MK, A₂ — середина BD. По теореме Фалеса MK ∥ BD, а A, A₁, A₂ лежат на одной прямой. Треугольники ACM и ACK равны по двум сторонам и углу 60° между ними, поэтому CM = CK. Медианы CA₁ и CA₂ равнобедренных треугольников CMK и CBD являются высотами. Плоскости CMK и CBD пересекаются по прямой l через C, параллельной BD. Обе медианы перпендикулярны l, поэтому угол A₁CA₂ — линейный угол искомого двугранного угла.</p>"
        + "<p>Из подобных прямоугольных треугольников MAA₁ и BAA₂:</p>"
        + line(r"\frac{AA_1}{AA_2}=\frac{AM}{AB}")
        + line(r"AA_2=CA_2=\frac{AB\sqrt3}{2}=" + value(q["AA2"]))
        + line(
            r"AA_1=\frac{AM}{AB}AA_2=\frac{"
            + value(q["t"])
            + "}{"
            + value(q["a"])
            + r"}\cdot "
            + bracket(q["AA2"])
            + "="
            + value(q["AA1"])
        )
        + line(
            r"A_1A_2=AA_2-AA_1="
            + value(q["AA2"])
            + "-"
            + bracket(q["AA1"])
            + "="
            + value(q["A1A2"])
        )
    )


def _cosines(m):
    q = m.q
    return (
        "<p>Применим теорему косинусов к треугольнику CAA₂:</p>"
        + line(r"\cos\angle AA_2C=\frac{AA_2^2+CA_2^2-AC^2}{2AA_2\cdot CA_2}")
        + line(
            r"\cos\angle AA_2C=\frac{"
            + bracket(q["AA2"])
            + "^2+"
            + bracket(q["CA2"])
            + "^2-"
            + bracket(q["a"])
            + r"^2}{2\cdot "
            + bracket(q["AA2"])
            + r"\cdot "
            + bracket(q["CA2"])
            + r"}=\frac{1}{3}"
        )
        + "<p>Теперь в треугольнике CA₁A₂:</p>"
        + line(r"CA_1^2=A_1A_2^2+CA_2^2-2A_1A_2\cdot CA_2\cos\angle AA_2C")
        + line(
            r"CA_1^2="
            + bracket(q["A1A2"])
            + "^2+"
            + bracket(q["CA2"])
            + r"^2-2\cdot "
            + bracket(q["A1A2"])
            + r"\cdot "
            + bracket(q["CA2"])
            + r"\cdot\frac{1}{3}="
            + value(q["CA1"] ** 2)
        )
        + line(r"CA_1=\sqrt{" + value(q["CA1"] ** 2) + "}=" + value(q["CA1"]))
        + "<p>Ещё раз используем теорему косинусов в том же треугольнике, чтобы найти искомый косинус:</p>"
        + line(r"\cos\angle A_1CA_2=\frac{CA_1^2+CA_2^2-A_1A_2^2}{2CA_1\cdot CA_2}")
        + line(
            r"\cos\angle A_1CA_2=\frac{"
            + bracket(q["CA1"])
            + "^2+"
            + bracket(q["CA2"])
            + "^2-"
            + bracket(q["A1A2"])
            + r"^2}{2\cdot "
            + bracket(q["CA1"])
            + r"\cdot "
            + bracket(q["CA2"])
            + "}="
            + value(m.answer)
        )
    )


def render(m, pictures):
    return parts(_volumes(m, pictures), _construction(m) + _cosines(m))
