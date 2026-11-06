"""Keep the rectangle proof and the same-side choice of the pyramid height."""

from ..probability.common import line
from .spatial_distance_proofs import parts
from .volume_section_format import bracket, value


def _rectangle():
    return "<p>Плоскость сечения ABNM перпендикулярна диаметру CD, лежащему в основании цилиндра. Поэтому эта плоскость перпендикулярна плоскости основания. Отрезки AM и BN — образующие цилиндра; они параллельны и равны. Следовательно, ABNM — параллелограмм. Поскольку AM и BN перпендикулярны основаниям цилиндра и, в частности, AB, этот параллелограмм является прямоугольником. Его диагонали AN и BM равны.</p>"


def _volume(m):
    q = m.q
    return (
        "<p>Площадь прямоугольника ABNM равна произведению хорды AB на высоту цилиндра:</p>"
        + line(
            r"S_{ABNM}=AB\cdot AM="
            + bracket(q["R"])
            + r"\cdot "
            + bracket(q["H"])
            + "="
            + value(q["section_area"])
        )
        + "<p>Обозначим радиус основания через R. Пусть O — центр основания с диаметром CD, H — точка пересечения CD и MN. Перпендикуляр из центра к хорде делит её пополам, поэтому MH = MN/2. По теореме Пифагора:</p>"
        + line(r"OH=\sqrt{OM^2-MH^2}=\sqrt{R^2-\left(\frac{R}{2}\right)^2}")
        + line(
            r"OH=\sqrt{"
            + bracket(q["R"])
            + "^2-"
            + bracket(q["half_chord"])
            + "^2}="
            + value(q["offset"])
        )
        + "<p>Точки C и O лежат по одну сторону от сечения. Поэтому высота CH пирамиды равна сумме CO и OH:</p>"
        + line(
            r"CH=CO+OH="
            + value(q["R"])
            + "+"
            + value(q["offset"])
            + "="
            + value(q["pyramid_height"])
        )
        + "<p>По формуле объёма пирамиды:</p>"
        + line(r"V=\frac13 S_{ABNM}\cdot CH")
        + line(
            r"V=\frac13\cdot "
            + bracket(q["section_area"])
            + r"\cdot "
            + bracket(q["pyramid_height"])
            + "="
            + value(m.answer)
        )
    )


def render(m, pictures):
    return parts(pictures.get("image_1", "") + _rectangle(), _volume(m))
