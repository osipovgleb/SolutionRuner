"""Keep the parent's projection argument before its cosine-law alternative."""

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value
from .spatial_distance_proofs import parts
from .spatial_metric_proofs import picture


def _base(m):
    q = m.q
    return (
        "<p>Точки D и E делят стороны AC и AB в одинаковом отношении, поэтому DE ∥ BC. Треугольник ADE равносторонний, и:</p>"
        + line("AD=AE=" + value(q["AD"]))
        + line(r"DE=\frac{AD}{AC}BC=" + value(q["DE"]))
        + (
            "<p>При AD/AC = 2/3 середина DE совпадает с центром O основания.</p>"
            if m.names[0] == "plain" and m.symbols["section_foot"] == "O"
            else ""
        )
    )


def _center(m):
    return (
        "<p>Пусть O — центр основания. В треугольнике ABC:</p>"
        + line(r"\frac{AE}{EB}=\frac{AD}{DC}=2")
        + _base(m)
        + "<p>Середина DE лежит на медиане из A и делит эту медиану в отношении 2 : 1. Центр равностороннего треугольника делит медиану в том же отношении, поэтому O лежит на DE и является его серединой. Следовательно, плоскость EDL содержит O.</p>"
    )


def _midpoint(m):
    q, foot = m.q, m.symbols["section_foot"]
    if foot == "O":
        return line(
            "KO=AO-AK=" + value(q["R"]) + "-" + bracket(q["AK"]) + "=" + value(q["KO"])
        )
    if foot == "K":
        return (
            "<p>Середина DE лежит на медиане из A. Расстояние до неё равно AD/AC от всей медианы, длина которой равна 3AO/2:</p>"
            + line(
                r"\frac{3AD}{2AB}AO=\frac{3\cdot "
                + bracket(q["AD"])
                + r"}{2\cdot "
                + bracket(q["a"])
                + r"}\cdot "
                + bracket(q["R"])
                + "="
                + value(q["AK"])
                + "=AK"
            )
            + "<p>Поэтому K — середина DE. Отрезок LK перпендикулярен основанию и DE, то есть является высотой сечения.</p>"
        )
    return (
        "<p>Обозначим середину DE через H. Она лежит на медиане из A; длина медианы равна 3AO/2. Из подобия треугольников:</p>"
        + line(
            r"AH=\frac{3AD}{2AB}AO=\frac{3\cdot "
            + bracket(q["AD"])
            + r"}{2\cdot "
            + bracket(q["a"])
            + r"}\cdot "
            + bracket(q["R"])
            + "="
            + value(q["AH"])
        )
        + line(
            r"KH=\left|AH-AK\right|=\left|"
            + value(q["AH"])
            + "-"
            + bracket(q["AK"])
            + r"\right|="
            + value(q["KH"])
        )
    )


def _projection(m):
    q, foot = m.q, m.symbols["section_foot"]
    height = "L" + foot
    return (
        "<p>Пусть O — центр основания. Рассмотрим прямоугольный треугольник AMO. Опустим из L перпендикуляр LK на AO; LK ∥ MO:</p>"
        + line(
            "AL=AM-LM=" + value(q["e"]) + "-" + bracket(q["LM"]) + "=" + value(q["AL"])
        )
        + line(
            r"AO=\frac{AB}{\sqrt{3}}=\frac{"
            + value(q["a"])
            + r"}{\sqrt{3}}="
            + value(q["R"])
        )
        + line(
            r"AK=\frac{AL}{AM}AO=\frac{"
            + value(q["AL"])
            + "}{"
            + value(q["e"])
            + r"}\cdot "
            + bracket(q["R"])
            + "="
            + value(q["AK"])
        )
        + _midpoint(m)
        + line(
            r"LK=\sqrt{AL^2-AK^2}=\sqrt{"
            + bracket(q["AL"])
            + "^2-"
            + bracket(q["AK"])
            + "^2}="
            + value(q["LK"])
        )
        + (
            line(
                height
                + r"=\sqrt{LK^2+K"
                + foot
                + r"^2}=\sqrt{"
                + bracket(q["LK"])
                + "^2+"
                + bracket(q["KO"] if foot == "O" else q["KH"])
                + "^2}="
                + value(q["section_height"])
            )
            if foot != "K"
            else ""
        )
        + "<p>Боковые грани AMB и AMC равны, поэтому LD = LE. Треугольник DLE — искомое сечение, а "
        + height
        + " — его высота:</p>"
        + line(r"S_{DLE}=\frac{1}{2}DE\cdot " + height)
        + line(
            r"S_{DLE}=\frac{1}{2}\cdot "
            + bracket(q["DE"])
            + r"\cdot "
            + bracket(q["section_height"])
            + "="
            + value(m.answer)
        )
    )


def _cosine(m, pictures):
    q, foot = m.q, m.symbols["section_foot"]
    title = (
        "Приведём другое решение пункта б)."
        if m.names[0] == "center"
        else "Приведём другое решение."
    )
    return (
        "<p><b>"
        + title
        + "</b></p>"
        + pictures.get("image_2", "")
        + "<p>Рассмотрим равнобедренную боковую грань AMB. Косинус угла BAM найдём с помощью половины основания AB. Затем применим теорему косинусов к ALE:</p>"
        + line(
            r"\cos\angle BAM=\frac{AB}{2AM}=\frac{"
            + value(q["a"])
            + r"}{2\cdot "
            + bracket(q["e"])
            + "}="
            + value(q["a"] / (2 * q["e"]))
        )
        + line(r"LE^2=AL^2+AE^2-2AL\cdot AE\cos\angle BAM")
        + line(
            r"LE^2="
            + bracket(q["AL"])
            + "^2+"
            + bracket(q["AE"])
            + r"^2-2\cdot "
            + bracket(q["AL"])
            + r"\cdot "
            + bracket(q["AE"])
            + r"\cdot "
            + bracket(q["a"] / (2 * q["e"]))
            + "="
            + value(q["LE2"])
        )
        + "<p>В равнобедренном треугольнике DLE высота проходит через середину DE, поэтому:</p>"
        + line(
            "E"
            + foot
            + r"=\frac{DE}{2}=\frac{"
            + value(q["DE"])
            + "}{2}="
            + value(q["DE"] / 2)
        )
        + line(
            "L"
            + foot
            + r"=\sqrt{LE^2-E"
            + foot
            + r"^2}=\sqrt{"
            + value(q["LE2"])
            + "-"
            + bracket(q["DE"] / 2)
            + "^2}="
            + value(q["section_height"])
        )
        + line(
            r"S_{DLE}=\frac{1}{2}DE\cdot L"
            + foot
            + r"=\frac{1}{2}\cdot "
            + bracket(q["DE"])
            + r"\cdot "
            + bracket(q["section_height"])
            + "="
            + value(m.answer)
        )
    )


def render(m, pictures):
    calculation = _projection(m) + _cosine(m, pictures)
    if m.names[0] == "center":
        return picture(pictures) + parts(_center(m), calculation)
    return picture(pictures) + _base(m) + calculation
