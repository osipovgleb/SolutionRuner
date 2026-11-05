"""The parent's equal-side proof and constant section altitude determine height."""

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value
from .spatial_distance_proofs import parts


def render(m, pictures):
    q = m.q
    first = (
        pictures.get("image_1", "")
        + "<p>Прямоугольные треугольники A₁C₁M и BCM равны по двум катетам: A₁C₁ = BC как стороны правильных оснований, а C₁M = CM по условию. Следовательно, A₁M = BM. Треугольник A₁MB равнобедренный.</p>"
    )
    second = (
        "<p>Пусть O — середина A₁B, а высота призмы CC₁ = 2x, где x &gt; 0. По теореме Пифагора:</p>"
        + line(r"A_1B=\sqrt{BB_1^2+A_1B_1^2}=\sqrt{4x^2+" + bracket(q["a"]) + "^2}")
        + line(r"A_1O^2=\frac{A_1B^2}{4}=x^2+" + value(q["a"] ** 2 / 4))
        + line(r"A_1M^2=A_1C_1^2+C_1M^2=" + value(q["a"] ** 2) + "+x^2")
        + "<p>В равнобедренном треугольнике медиана MO является высотой. Найдём её длину в прямоугольном треугольнике A₁MO:</p>"
        + line(
            r"MO^2=A_1M^2-A_1O^2=("
            + value(q["a"] ** 2)
            + "+x^2)-(x^2+"
            + value(q["a"] ** 2 / 4)
            + ")="
            + value(q["altitude"] ** 2)
        )
        + line("MO=" + value(q["altitude"]))
        + "<p>Используем данную площадь сечения, чтобы найти x:</p>"
        + line(r"S_{A_1MB}=\frac{MO\cdot A_1B}{2}=MO\sqrt{x^2+\frac{AB^2}{4}}")
        + line(
            r"\sqrt{x^2+"
            + value(q["a"] ** 2 / 4)
            + r"}=\frac{"
            + value(q["area"])
            + "}{"
            + value(q["altitude"])
            + "}="
            + value(q["area"] / q["altitude"])
        )
        + line(
            "x^2="
            + bracket(q["area"] / q["altitude"])
            + "^2-"
            + bracket(q["a"] ** 2 / 4)
            + "="
            + value(q["x"] ** 2)
        )
        + line("x=" + value(q["x"]))
        + line(r"CC_1=2x=2\cdot " + bracket(q["x"]) + "=" + value(m.answer))
    )
    return parts(first, second)
