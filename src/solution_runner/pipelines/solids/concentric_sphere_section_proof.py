"""Prove both inclusions of a disk, then transfer the squared-radius difference."""

from ..probability.common import line
from .spatial_distance_proofs import parts
from .volume_section_format import value


def _disk():
    return (
        "<p>Пусть O — центр шара радиуса R, F — основание перпендикуляра из O на секущую плоскость α. Для любой точки X этой плоскости по теореме Пифагора:</p>"
        + line(r"OX^2=OF^2+FX^2")
        + "<p>Если X принадлежит шару, то OX ≤ R, поэтому:</p>"
        + line(r"FX\le\sqrt{R^2-OF^2}")
        + "<p>Следовательно, X лежит в круге с центром F и радиусом √(R² − OF²). Обратно, если X лежит в этом круге, то:</p>"
        + line(r"OX^2=OF^2+FX^2\le R^2")
        + "<p>Значит, X принадлежит шару и плоскости α. Доказаны оба включения: сечение шара плоскостью α есть указанный круг.</p>"
    )


def _areas(m):
    q = m.q
    return (
        "<p>Рассмотрим сечение, проходящее через общий центр шаров и центры круговых сечений. На рисунке A — точка касания плоскости β с меньшим шаром. Отрезки FD, AB и CF — радиусы соответствующих круговых сечений:</p>"
        + line(r"S_{\alpha}=\pi FD^2=" + value(q["alpha_area"]))
        + line(r"S_{\beta}=\pi AB^2=" + value(q["beta_area"]))
        + "<p>Из прямоугольных треугольников OFC и OFD:</p>"
        + line(r"OF^2=OC^2-CF^2=OD^2-FD^2")
        + "<p>Так как OC = OB и OD = OA — радиусы соответствующих шаров, а треугольник OAB прямоугольный:</p>"
        + line(r"CF^2=OC^2-OD^2+FD^2=OB^2-OA^2+FD^2=AB^2+FD^2")
        + "<p>Поэтому искомая площадь равна сумме двух данных площадей:</p>"
        + line(r"S=\pi CF^2=\pi AB^2+\pi FD^2")
        + line(
            "S="
            + value(q["beta_area"])
            + "+"
            + value(q["alpha_area"])
            + "="
            + value(m.answer)
        )
        + "<p><b>Примечание.</b> В вычислении используется только квадрат OF, поэтому решение не зависит от того, по одну сторону от центра шаров лежат плоскости α и β или по разные стороны.</p>"
    )


def render(m, pictures):
    return parts(pictures.get("image_1", "") + _disk(), _areas(m))
