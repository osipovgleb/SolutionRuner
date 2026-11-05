"""Parent vertical-plane and centroid constructions with reviewed auxiliary names."""

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value
from .spatial_distance_proofs import parts
from .spatial_metric_proofs import picture


def vertical(m, pictures):
    q = m.q
    median = m.names[0]
    foot = m.symbols.get("foot", "L")
    left = m.symbols.get("lower_left", "P")
    right = m.symbols.get("lower_right", "Q")
    base = left + right
    height = "K" + foot
    ce = "C" + median
    first = (
        "<p>Прямая MN — средняя линия треугольника ASB, поэтому MN ∥ AB. Плоскость α пересекает основание по прямой "
        + base.replace("_1", "₁")
        + ", параллельной MN. Пусть "
        + median
        + " — середина AB, O — центр основания, K — пересечение S"
        + median
        + " и MN, а "
        + foot.replace("_1", "₁")
        + " — пересечение "
        + ce
        + " с α.</p>"
        + "<p>Плоскости SC"
        + median
        + " и α перпендикулярны основанию. Поэтому их линия пересечения "
        + height.replace("_1", "₁")
        + " перпендикулярна основанию и параллельна SO. Точка K — середина S"
        + median
        + ", значит, в треугольнике S"
        + median
        + "O отрезок "
        + height.replace("_1", "₁")
        + " является средней линией:</p>"
        + line(median + foot + r"=\frac{" + median + r"O}{2}=\frac{" + ce + "}{6}")
        + line("C" + foot + "=" + ce + "-" + median + foot + r"=\frac{5}{6}" + ce)
        + line(r"\frac{C" + foot + "}{" + foot + median + r"}=\frac{5/6}{1/6}=5")
        + "<p>Таким образом, медиана делится в отношении 5 : 1, считая от C.</p>"
    )
    second = (
        "<p>Сечение — трапеция MN"
        + right.replace("_1", "₁")
        + left.replace("_1", "₁")
        + ". Из средней линии и подобия треугольников основания:</p>"
        + line(r"MN=\frac{AB}{2}=\frac{" + value(q["a"]) + "}{2}=" + value(q["upper"]))
        + line(
            base
            + r"=\frac{5}{6}AB=\frac{5}{6}\cdot "
            + bracket(q["a"])
            + "="
            + value(q["lower"])
        )
        + "<p>Высота трапеции равна половине высоты пирамиды. Найдём SO в прямоугольном треугольнике SCO:</p>"
        + line(
            r"CO=\frac{AB}{\sqrt{3}}=\frac{"
            + value(q["a"])
            + r"}{\sqrt{3}}="
            + value(q["R"])
        )
        + line(
            r"SO=\sqrt{SC^2-CO^2}=\sqrt{"
            + bracket(q["e"])
            + "^2-"
            + bracket(q["R"])
            + "^2}="
            + value(q["H"])
        )
        + line(
            height
            + r"=\frac{SO}{2}=\frac{"
            + value(q["H"])
            + "}{2}="
            + value(q["section_height"])
        )
        + line("S_{MN" + right + left + r"}=\frac{MN+" + base + r"}{2}\cdot " + height)
        + line(
            "S_{MN"
            + right
            + left
            + r"}=\frac{"
            + value(q["upper"])
            + "+"
            + value(q["lower"])
            + r"}{2}\cdot "
            + bracket(q["section_height"])
            + "="
            + value(m.answer)
        )
    )
    return picture(pictures) + parts(first, second)


def _perpendicular_claim():
    return "<p>Пусть O — центр основания. Проекция MC на основание — прямая OC, лежащая на диагонали AC. Диагонали квадрата перпендикулярны: AC ⟂ BD. По теореме о трёх перпендикулярах MC ⟂ BD.</p>"


def _median_construction(m):
    f = m.symbols.get("on_MA", "F")
    g = m.symbols.get("on_MC", "G")
    cross = m.symbols.get("cross_line", f + g)
    if m.names[0] == "point":
        return (
            "<p>Через данную точку N проведём "
            + cross
            + " ∥ AC до пересечения с MA в точке "
            + f
            + ". Пусть O — центр основания, P — пересечение "
            + cross
            + " и MO. Из подобия треугольников M"
            + f
            + g
            + " и MAC:</p>"
            + line(r"\frac{MP}{MO}=\frac{MN}{MC}=\frac{2}{3}")
            + line(r"\frac{MP}{PO}=2")
            + "<p>Следовательно, P — точка пересечения медиан треугольника MBD. Прямая BP пересекает MD в его середине E.</p>"
        )
    return (
        "<p>Пусть E — середина MD, O — центр основания. В треугольнике MBD отрезки BE и MO — медианы. Их пересечение P делит MO в отношении 2 : 1 от вершины M. Проведём через P отрезок "
        + cross
        + ", параллельный AC, где "
        + f
        + " лежит на MA, а "
        + g
        + " — на MC.</p>"
        + line(r"\frac{MP}{PO}=2")
        + line(r"\frac{M" + g + "}{" + g + r"C}=\frac{MP}{PO}=2")
    )


def median(m, pictures):
    q = m.q
    cross = m.symbols.get("cross_line", "FG")
    f = m.symbols.get("on_MA", "F")
    g = m.symbols.get("on_MC", "G")
    boundary = "B" + (g + "E" + f if m.names[0] == "point" else f + "E" + g)
    construction = _median_construction(m)
    first = (
        _perpendicular_claim()
        if m.names[1] == "perpendicular"
        else construction + "<p>Это и доказывает требуемое отношение на MC.</p>"
    )
    second = (construction if m.names[1] == "perpendicular" else "") + (
        "<p>Четырёхугольник "
        + boundary
        + " — искомое сечение. По подобию в треугольнике MAC:</p>"
        + line(
            cross
            + r"=\frac{2}{3}AC=\frac{2\sqrt{2}}{3}\cdot AB=\frac{2\sqrt{2}}{3}\cdot "
            + bracket(q["a"])
            + "="
            + value(q["FG"])
        )
        + "<p>BE — медиана треугольника MBD. Найдём её длину по формуле медианы:</p>"
        + line(r"BD=AB\sqrt{2}=" + value(q["diagonal"]))
        + line(r"BE=\frac{\sqrt{2BD^2+2MB^2-MD^2}}{2}=\frac{\sqrt{4AB^2+MB^2}}{2}")
        + line(
            r"BE=\frac{\sqrt{4\cdot "
            + bracket(q["a"])
            + "^2+"
            + bracket(q["e"])
            + "^2}}{2}="
            + value(q["BE"])
        )
        + "<p>AC перпендикулярна BD и MO, поэтому AC перпендикулярна плоскости MBD. Следовательно, диагональ "
        + cross
        + ", параллельная AC, перпендикулярна диагонали BE сечения. Площадь четырёхугольника равна половине произведения этих диагоналей:</p>"
        + line("S_{" + boundary + r"}=\frac{BE\cdot " + cross + "}{2}")
        + line(
            "S_{"
            + boundary
            + r"}=\frac{"
            + bracket(q["BE"])
            + r"\cdot "
            + bracket(q["FG"])
            + "}{2}="
            + value(m.answer)
        )
    )
    return picture(pictures) + parts(first, second)


def render(m, pictures):
    return (
        vertical(m, pictures)
        if m.mode == "triangle_vertical_section_area"
        else median(m, pictures)
    )
