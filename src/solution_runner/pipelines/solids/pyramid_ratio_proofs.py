"""Keep the parents' similarity, common-height and midpoint-volume arguments."""

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value


def scale(m):
    k = m.given[0]
    rows = "<p>Обозначим коэффициент изменения линейных размеров через k:</p>" + line(
        "k=" + value(k)
    )
    if m.kind == "scale_height":
        return (
            rows
            + line("H_1=kH_0")
            + line("B_1=B_0")
            + "<p>Площадь основания не меняется. По формуле объёма пирамиды получаем:</p>"
            + line(r"V_0=\frac{1}{3}B_0H_0")
            + line(r"V_1=\frac{1}{3}B_1H_1=kV_0")
            + line(r"\frac{V_1}{V_0}=" + value(m.answer))
        )
    if m.kind == "scale_volume":
        return (
            rows
            + "<p>При изменении всех рёбер тетраэдры подобны. Это следует также из формулы объёма правильного тетраэдра:</p>"
            + line("a_1=ka_0")
            + line(r"V_0=\frac{\sqrt{2}}{12}a_0^3")
            + line(r"V_1=\frac{\sqrt{2}}{12}a_1^3")
            + line(r"\frac{V_1}{V_0}=k^3")
            + line(r"\frac{V_1}{V_0}=" + bracket(k) + "^3=" + value(m.answer))
        )
    if m.body == "правильного тетраэдра":
        return (
            rows
            + "<p>Площадь каждой равносторонней грани пропорциональна квадрату её стороны. Все четыре грани меняются в одном отношении:</p>"
            + line(r"A_0=\frac{\sqrt{3}}{4}a_0^2")
            + line(r"A_1=\frac{\sqrt{3}}{4}(ka_0)^2=k^2A_0")
            + line("S_0=4A_0")
            + line("S_1=4A_1=k^2S_0")
            + line(r"\frac{S_1}{S_0}=" + bracket(k) + "^2=" + value(m.answer))
        )
    return (
        rows
        + "<p>В каждой треугольной грани основание и высота меняются в k раз, поэтому площадь меняется в квадрате этого отношения. Многоугольную грань можно разбить на треугольники. То же верно для суммы площадей всех граней:</p>"
        + line("a_1=ka_0")
        + line("h_1=kh_0")
        + line(r"A_1=\frac{1}{2}a_1h_1=k^2A_0")
        + line("S_1=k^2S_0")
        + line(r"\frac{S_1}{S_0}=" + bracket(k) + "^2=" + value(m.answer))
    )


def _quarter(m):
    midpoint = m.kind == "square_midpoint"
    intro = (
        "<p>Основание ABC составляет половину квадратного основания SABCD. Точка E — середина ребра SB, поэтому высота пирамиды EABC также вдвое меньше высоты исходной пирамиды:</p>"
        if midpoint
        else "<p>Средняя линия отсекает треугольник, подобный основанию с коэффициентом 1/2. Исходная и отсечённая пирамиды имеют общую высоту:</p>"
    )
    return (
        intro
        + line(r"k=\frac{1}{2}")
        + line(r"B_1=\frac{B_0}{2}" if midpoint else r"B_1=k^2B_0=\frac{B_0}{4}")
        + line(r"H_1=\frac{H_0}{2}" if midpoint else "H_1=H_0")
        + "<p>Отношение объёмов равно произведению отношений площадей оснований и высот:</p>"
        + line(r"\frac{V_1}{V_0}=\frac{B_1H_1}{B_0H_0}=\frac{1}{4}")
        + line(r"V_1=\frac{V_0}{4}")
        + line(r"V_1=\frac{" + value(m.given[0]) + "}{4}=" + value(m.answer))
    )


def _edge(m):
    volume, a, b = m.given
    large = max(a, b)
    total = a + b
    return (
        "<p>Две полученные пирамиды можно рассматривать с общей площадью основания. Их высоты, а значит и объёмы, относятся как части разделённого ребра:</p>"
        + line("r_1=" + value(a))
        + line("r_2=" + value(b))
        + line(r"\frac{V_1}{V_2}=\frac{r_1}{r_2}")
        + "<p>Выберем большую долю всего объёма независимо от порядка чисел в отношении:</p>"
        + line("r_1+r_2=" + value(total))
        + line(
            r"k=\frac{" + value(large) + "}{" + value(total) + "}=" + value(m.q["k"])
        )
        + line("V=kV_0")
        + line(
            "V="
            + bracket(m.q["k"])
            + r"\cdot"
            + bracket(volume)
            + "="
            + value(m.answer)
        )
    )


def _hex(m):
    return (
        "<p>У пирамид SABC и SABCDEF общая высота. Найдём отношение площадей оснований, обозначив сторону шестиугольника через a:</p>"
        + line(r"B=\frac{3\sqrt{3}}{2}a^2")
        + line(r"B_p=\frac{\sqrt{3}}{4}a^2")
        + line(r"\frac{B}{B_p}=6")
        + "<p>Объёмы пирамид с общей высотой относятся как площади оснований:</p>"
        + line(r"\frac{V}{V_p}=\frac{B}{B_p}=6")
        + line("V=6V_p")
        + line(r"V=6\cdot" + bracket(m.given[0]) + "=" + value(m.answer))
    )


def _sixth(m):
    cube = m.kind == "cube_center"
    if cube:
        return (
            "<p>Основание пирамиды — грань куба со стороной a. Её вершина находится в центре куба, поэтому высота вдвое меньше ребра:</p>"
            + line("V_0=a^3")
            + line("B=a^2")
            + line(r"H=\frac{a}{2}")
            + "<p>Применим формулу объёма пирамиды:</p>"
            + line(r"V=\frac{1}{3}BH")
            + line(r"V=\frac{a^3}{6}=\frac{V_0}{6}")
            + line(r"V=\frac{" + value(m.given[0]) + "}{6}=" + value(m.answer))
            + "<p><b>Примечание.</b> Куб состоит из шести таких пирамид с общей вершиной в центре, поэтому их объёмы равны:</p>"
            + line("6V=V_0")
        )
    return (
        "<p>Основание ABC составляет половину параллелограмма ABCD. Высота пирамиды из вершины B₁ равна расстоянию между основаниями параллелепипеда:</p>"
        + line("V_0=BH")
        + line(r"B_p=\frac{B}{2}")
        + line("H_p=H")
        + "<p>Используем формулу объёма пирамиды. Она применима и к наклонному параллелепипеду:</p>"
        + line(r"V=\frac{1}{3}B_pH_p")
        + line(r"V=\frac{V_0}{6}")
        + line(r"V=\frac{" + value(m.given[0]) + "}{6}=" + value(m.answer))
    )


def section(m):
    reason = (
        "В правильном тетраэдре скрещивающиеся рёбра перпендикулярны. Стороны сечения — средние линии соответствующих треугольных граней, поэтому они параллельны этим рёбрам и образуют квадрат."
        if m.kind == "tetra_section"
        else "Каждая сторона сечения является средней линией боковой грани. Плоскость через середины боковых рёбер параллельна основанию, поэтому сечение — квадрат."
    )
    return (
        "<p>"
        + reason
        + " Обозначим сторону сечения через t:</p>"
        + line(r"k=\frac{1}{2}")
        + line("t=ka")
        + line(r"t=\frac{" + value(m.given[0]) + "}{2}=" + value(m.q["t"]))
        + "<p>Площадь квадрата равна квадрату его стороны:</p>"
        + line("S=t^2")
        + line("S=" + bracket(m.q["t"]) + "^2=" + value(m.answer))
    )


def render(m):
    if m.kind.startswith("scale_"):
        return scale(m)
    if m.kind.endswith("_section"):
        return section(m)
    if m.kind in {"square_midpoint", "midline_cut"}:
        return _quarter(m)
    return {
        "edge_cut": _edge,
        "hex_whole": _hex,
        "cube_center": _sixth,
        "box_tetrahedron": _sixth,
    }[m.kind](m)
