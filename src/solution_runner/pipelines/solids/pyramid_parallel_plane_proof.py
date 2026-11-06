"""Parent Thales construction and acute linear angle with explicit point labels."""

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value
from .spatial_distance_proofs import parts


def _names(m):
    return ("L", "N", "K", "M") if m.names == ("L", "N") else ("K", "M", "L", "N")


def _proof(m, pictures):
    q = m.q
    ab, sc, ac, sb = _names(m)
    return (
        pictures.get("image_1", "")
        + "<p>Через "
        + ab
        + " и "
        + sc
        + " проведём в гранях ABC и SBC прямые "
        + ab
        + ac
        + " и "
        + sc
        + sb
        + " параллельно BC. Точки "
        + ac
        + " и "
        + sb
        + " лежат на AC и SB соответственно; четырёхугольник "
        + ab
        + ac
        + sc
        + sb
        + " — сечение плоскостью α. По теореме Фалеса:</p>"
        + line(
            r"\frac{A"
            + ac
            + "}{"
            + ac
            + r"C}=\frac{A"
            + ab
            + "}{"
            + ab
            + r"B}=\frac{S"
            + sc
            + "}{"
            + sc
            + r"C}=\frac{"
            + value(q["p"])
            + "}{"
            + value(q["q"])
            + "}"
        )
        + "<p>По теореме, обратной теореме Фалеса, "
        + sc
        + ac
        + " ∥ SA. Точка A не лежит на следе "
        + ab
        + ac
        + " плоскости α в основании, поэтому SA не лежит в α. Следовательно, плоскость α параллельна SA.</p>"
    )


def _angle(m):
    q = m.q
    ab, sc, ac, sb = _names(m)
    return (
        "<p>Пусть T — середина BC, P — пересечение AT и "
        + ab
        + ac
        + ", Q — пересечение ST и "
        + sb
        + sc
        + ". Медианы AT и ST перпендикулярны BC, поэтому плоскость SAT перпендикулярна BC. Она пересекает α и SBC по PQ и QT, перпендикулярным общей линии "
        + sb
        + sc
        + ". Следовательно, угол PQT или смежный с ним является меньшим углом между плоскостями. По подобию в треугольнике SAT имеем PQ ∥ SA. Поэтому искомый угол — меньший угол между SA и ST.</p>"
        + line(r"AT=\frac{AB\sqrt3}{2}=" + value(q["AH"]))
        + line(
            r"ST=\sqrt{SB^2-BT^2}=\sqrt{"
            + bracket(q["e"])
            + r"^2-\left(\frac{"
            + value(q["a"])
            + r"}{2}\right)^2}="
            + value(q["l"])
        )
        + "<p>По теореме косинусов в треугольнике SAT:</p>"
        + line(r"\cos\angle AST=\frac{SA^2+ST^2-AT^2}{2SA\cdot ST}")
        + line(
            r"\cos\angle AST=\frac{"
            + bracket(q["e"])
            + "^2+"
            + bracket(q["l"])
            + "^2-"
            + bracket(q["AH"])
            + r"^2}{2\cdot "
            + bracket(q["e"])
            + r"\cdot "
            + bracket(q["l"])
            + "}="
            + value((q["e"] ** 2 - q["a"] ** 2 / 2) / (q["e"] * q["l"]))
        )
        + "<p>Для меньшего угла φ между плоскостями возьмём модуль:</p>"
        + line(r"\cos\varphi=|\cos\angle AST|=" + value(q["cosine"]))
    )


def render(m, pictures):
    return parts(_proof(m, pictures), _angle(m))
