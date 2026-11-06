"""Three parent endings find the smaller angle between rectangle diagonals."""

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value
from .spatial_distance_proofs import parts


def _claim(m):
    first, second = m.names
    vertices = "BC и DA" if first == "DC" else "AB и DC"
    return (
        "<p>Через E проведём EK параллельно "
        + first
        + ", а EM — параллельно "
        + second
        + ". Точки K и M лежат на рёбрах "
        + vertices
        + " соответственно. Это средние линии соответствующих треугольников. Через K проведём KF параллельно EM; точка F лежит на AC, и MF параллельна EK. Получили сечение EKFM — параллелограмм.</p>"
        + "<p>По условию "
        + first
        + " ⟂ "
        + second
        + ". Следовательно, EK ⟂ EM. Параллелограмм с прямым углом является прямоугольником.</p>"
    )


def _calculation(m):
    q = m.q
    long_first = q["first"] >= q["second"]
    angle, short = ("EOM", "EM") if long_first else ("EOK", "EK")
    length = min(q["first"], q["second"])
    return (
        "<p>Отрезки EK и EM — средние линии треугольников, поэтому:</p>"
        + line(r"EK=\frac{" + m.names[0] + "}{2}=" + value(q["first"]))
        + line(r"EM=\frac{" + m.names[1] + "}{2}=" + value(q["second"]))
        + line(
            r"MK=EF=\sqrt{EK^2+EM^2}=\sqrt{"
            + bracket(q["first"])
            + "^2+"
            + bracket(q["second"])
            + "^2}="
            + value(q["diagonal"])
        )
        + "<p>Пусть O — точка пересечения диагоналей. Диагонали прямоугольника равны и делятся точкой пересечения пополам:</p>"
        + line(r"MO=OK=EO=OF=\frac{MK}{2}=" + value(q["radius"]))
        + "<p>Выберем треугольник с меньшей стороной прямоугольника в основании. Тогда угол "
        + angle
        + " — меньший угол между диагоналями. По теореме косинусов:</p>"
        + line(r"\cos\angle " + angle + r"=\frac{2EO^2-" + short + r"^2}{2EO^2}")
        + line(
            r"\cos\angle "
            + angle
            + r"=\frac{2\cdot "
            + bracket(q["radius"])
            + "^2-"
            + bracket(length)
            + r"^2}{2\cdot "
            + bracket(q["radius"])
            + "^2}="
            + value(q["cosine"])
        )
    )


def _alternatives(m):
    q = m.q
    small, large = min(q["first"], q["second"]), max(q["first"], q["second"])
    return (
        "<p><b>Другой способ. Через площадь сечения.</b> Пусть α — меньший угол между диагоналями. Вычислим площадь прямоугольника двумя способами:</p>"
        + line(r"S=EK\cdot EM=\frac{MK\cdot EF\sin\alpha}{2}")
        + line(
            r"\sin\alpha=\frac{2EK\cdot EM}{MK\cdot EF}=\frac{2\cdot "
            + bracket(q["first"])
            + r"\cdot "
            + bracket(q["second"])
            + "}{"
            + bracket(q["diagonal"])
            + "^2}="
            + value(q["sine"])
        )
        + line(r"\alpha=\arcsin " + bracket(q["sine"]))
        + "<p><b>Ещё один способ. Через половину угла.</b> В равнобедренном треугольнике с вершиной O и меньшей стороной прямоугольника в основании проведём высоту. Она делит угол α пополам. Катеты полученного прямоугольного треугольника равны половинам меньшей и большей сторон сечения:</p>"
        + line(
            r"\tan\frac{\alpha}{2}=\frac{"
            + bracket(small)
            + "}{"
            + bracket(large)
            + "}="
            + value(q["half_tangent"])
        )
        + line(r"\alpha=2\arctan " + bracket(q["half_tangent"]))
    )


def render(m, pictures):
    return parts(
        pictures.get("image_1", "") + _claim(m), _calculation(m)
    ) + _alternatives(m)
