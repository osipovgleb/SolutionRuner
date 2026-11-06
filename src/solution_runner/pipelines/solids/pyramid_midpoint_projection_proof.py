"""The parent's projected median, midpoint and right-triangle calculation."""

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value
from .spatial_distance_proofs import parts


def _claim(m):
    common = "<p>Пусть O — центр основания, N — середина BC, M — середина AS. Проекция S на основание — O. Медиана AN равностороннего треугольника ABC проходит через O и является высотой.</p>"
    if m.names[0] == "perpendicular":
        return (
            common
            + "<p>Следовательно, AO ⟂ BC. Прямая AO — проекция AS на основание. По теореме о трёх перпендикулярах AS ⟂ BC, что и требовалось доказать.</p>"
        )
    return (
        common
        + "<p>Точка O делит медиану AN в отношении AO : ON = 2 : 1. Проекция M — точка M₁ на AO. В треугольнике ASO отрезок MM₁ параллелен SO; поскольку M — середина AS, M₁ — середина AO.</p>"
        + line(r"AM_1=M_1O=\frac{AO}{2}=\frac{AN}{3}=ON")
        + "<p>Таким образом, проекции M и S, то есть точки M₁ и O, делят высоту AN на три равные части.</p>"
    )


def _calculation(m):
    q = m.q
    return (
        "<p>Найдём медиану равностороннего треугольника ABC:</p>"
        + line(
            r"AN=\frac{AB\sqrt3}{2}=\frac{"
            + bracket(q["a"])
            + r"\sqrt3}{2}="
            + value(q["AN"])
        )
        + "<p>Проекция прямой MN на основание — прямая M₁N, совпадающая с AN. Значит, искомый угол равен MNM₁. Так как MM₁ ∥ SO, отрезок MM₁ — средняя линия треугольника ASO, а M₁ — середина AO:</p>"
        + line(
            r"AM_1=\frac{AO}{2}=\frac{AN}{3}=\frac{"
            + bracket(q["AN"])
            + "}{3}="
            + value(q["AM1"])
        )
        + line(
            r"M_1N=AN-AM_1="
            + value(q["AN"])
            + "-"
            + bracket(q["AM1"])
            + "="
            + value(q["M1N"])
        )
        + line(r"AM=\frac{AS}{2}=\frac{" + value(q["e"]) + "}{2}=" + value(q["AM"]))
        + "<p>В прямоугольном треугольнике AMM₁ по теореме Пифагора:</p>"
        + line(
            r"MM_1=\sqrt{AM^2-AM_1^2}=\sqrt{"
            + bracket(q["AM"])
            + "^2-"
            + bracket(q["AM1"])
            + "^2}="
            + value(q["MM1"])
        )
        + "<p>Теперь в прямоугольном треугольнике MM₁N:</p>"
        + line(
            r"\tan\angle MNM_1=\frac{MM_1}{M_1N}=\frac{"
            + bracket(q["MM1"])
            + "}{"
            + bracket(q["M1N"])
            + "}="
            + value(q["tan"])
        )
    )


def render(m, pictures):
    return parts(pictures.get("image_1", "") + _claim(m), _calculation(m))
