"""Keep the parallel-line translation and the source isosceles-triangle calculation."""

from ..probability.common import line
from .spatial_distance_proofs import parts
from .volume_section_format import bracket, value


def _claim(m):
    if m.names[2] == "angle_equal":
        return "<p>В правильном шестиугольнике BE ∥ CD. Вместо прямой CD рассмотрим параллельную ей прямую BE. Угол SBE острый, поэтому искомый угол между прямыми SB и CD равен углу SBE.</p>"
    plane, parallel, contained = (
        ("SBD", "AE", "BD") if m.names[2] == "SBD" else ("SBC", "AD", "BC")
    )
    return (
        "<p>В правильном шестиугольнике "
        + parallel
        + " ∥ "
        + contained
        + ". Прямая "
        + contained
        + " лежит в плоскости "
        + plane
        + ", а прямая "
        + parallel
        + " не лежит в этой плоскости. По признаку параллельности прямой и плоскости "
        + parallel
        + " ∥ ("
        + plane
        + ").</p>"
    )


def _angle(m):
    q = m.q
    first = (
        "<p>Большая диагональ правильного шестиугольника вдвое больше его стороны:</p>"
        + line(r"BE=2CD=2\cdot " + bracket(q["a"]) + "=" + value(q["chord"]))
        + line(r"SB=SE=" + value(q["e"]))
    )
    if q["chord"] == q["e"]:
        return (
            first
            + "<p>Треугольник SBE равносторонний, поэтому:</p>"
            + line(r"\angle SBE=60^{\circ}")
        )
    return (
        first
        + "<p>В равнобедренном треугольнике SBE применим теорему косинусов:</p>"
        + line(r"\cos\angle SBE=\frac{SB^2+BE^2-SE^2}{2SB\cdot BE}")
        + line(
            r"\cos\angle SBE=\frac{"
            + bracket(q["e"])
            + "^2+"
            + bracket(q["chord"])
            + "^2-"
            + bracket(q["e"])
            + r"^2}{2\cdot "
            + bracket(q["e"])
            + r"\cdot "
            + bracket(q["chord"])
            + "}="
            + value(q["cosine"])
        )
        + line(r"\angle SBE=\arccos " + bracket(q["cosine"]))
    )


def _cosine(m):
    q = m.q
    return (
        "<p>Прямая AD параллельна BC, поэтому искомый угол равен острому углу SBC. В равнобедренном треугольнике SBC проведём медиану и высоту SM:</p>"
        + line(
            r"BM=\frac{BC}{2}=\frac{" + value(q["a"]) + "}{2}=" + value(q["half_chord"])
        )
        + "<p>Из прямоугольного треугольника SBM:</p>"
        + line(r"\cos\angle SBC=\frac{BM}{SB}")
        + line(
            r"\cos\angle SBC=\frac{"
            + value(q["half_chord"])
            + "}{"
            + value(q["e"])
            + "}="
            + value(m.answer)
        )
    )


def render(m, pictures):
    return parts(
        pictures.get("image_1", "") + _claim(m),
        _angle(m) if m.names[1] == "angle" else _cosine(m),
    )
