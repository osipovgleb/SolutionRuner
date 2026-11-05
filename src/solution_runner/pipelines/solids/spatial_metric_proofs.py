"""Parent midpoint, symmetry and similar-triangle proofs for regular solids."""

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value
from .spatial_distance_proofs import parts


def picture(pictures):
    return pictures.get("image_1", pictures.get("box_distance_solution", ""))


def _midpoint(m, pictures):
    q = m.q
    lateral = m.names[0] == "AD"
    proof = (
        "<p>Пусть P — середина BD, а Q — середина BC. По теореме о средней линии MT ∥ CD ∥ QP и MT = QP = CD/2. Значит, MTPQ — параллелограмм. Кроме того, PT ∥ AB. Если O — центр основания, то CO ⟂ AB; по теореме о трёх перпендикулярах CD ⟂ AB. Поэтому PT ⟂ MT, и параллелограмм MTPQ является прямоугольником.</p>"
        if lateral
        else "<p>Пусть P — середина BD, а Q — середина CD. По теореме о средней линии TP ∥ AD ∥ MQ и TP = MQ = AD/2. Следовательно, TPQM — параллелограмм. При этом PQ ∥ BC. Если O — центр основания, то AO ⟂ BC; по теореме о трёх перпендикулярах AD ⟂ BC. Поэтому параллелограмм TPQM является прямоугольником.</p>"
    )
    if lateral:
        dimensions = (
            line(r"AO=\sqrt{AD^2-DO^2}")
            + line(
                r"AO=\sqrt{"
                + bracket(q["e"])
                + "^2-"
                + bracket(q["H"])
                + "^2}="
                + value(q["R"])
            )
            + line(r"AB=AO\sqrt{3}")
            + line("AB=" + bracket(q["R"]) + r"\cdot\sqrt{3}=" + value(q["a"]))
        )
        target = "AB"
    else:
        dimensions = (
            line(r"AO=\frac{AB}{\sqrt{3}}")
            + line(r"AO=\frac{" + value(q["a"]) + r"}{\sqrt{3}}=" + value(q["R"]))
            + line(r"AD=\sqrt{AO^2+DO^2}")
            + line(
                r"AD=\sqrt{"
                + bracket(q["R"])
                + "^2+"
                + bracket(q["H"])
                + "^2}="
                + value(q["e"])
            )
        )
        target = "AD"
    calculation = (
        "<p>По доказанному прямоугольнику PT перпендикулярен MT. Поэтому искомое расстояние равно PT. Найдём нужную сторону правильной пирамиды:</p>"
        + dimensions
        + "<p>По теореме о средней линии:</p>"
        + line(r"PT=\frac{" + target + "}{2}")
        + line(
            r"PT=\frac{" + value(q["a" if lateral else "e"]) + "}{2}=" + value(m.answer)
        )
    )
    return picture(pictures) + parts(proof, calculation)


def _hex(m, pictures):
    q = m.q
    x, u, v, y, z = m.names
    chord = u + v
    base = y + z
    height = y + "M"
    step = abs("ABCDEF".index(y) - "ABCDEF".index(z))
    step = min(step, 6 - step)
    coefficient = {1: "a", 2: r"a\sqrt{3}", 3: "2a"}[step]
    proof = (
        "<p>Обозначим центр правильного шестиугольника через O. Вершины "
        + u
        + " и "
        + v
        + " симметричны относительно диаметра, проходящего через "
        + x
        + ". Поэтому "
        + chord
        + " ⟂ O"
        + x
        + ". Проекцией S на плоскость основания является O, а проекцией S"
        + x
        + " — прямая O"
        + x
        + ". По теореме о трёх перпендикулярах S"
        + x
        + " ⟂ "
        + chord
        + ".</p>"
    )
    calculation = (
        "<p>В равнобедренном треугольнике S"
        + y
        + z
        + " проведём высоту SH к основанию "
        + base
        + " и перпендикуляр "
        + height
        + " к прямой S"
        + z
        + ". Длина "
        + height
        + " и есть искомое расстояние. В правильном шестиугольнике получаем:</p>"
        + line("a=" + value(q["a"]))
        + line(base + "=" + coefficient + "=" + value(q["b"]))
        + line("S" + y + "=S" + z + "=" + value(q["e"]))
        + line(r"SH=\sqrt{S" + y + r"^2-\left(\frac{" + base + r"}{2}\right)^2}")
        + line(
            r"SH=\sqrt{"
            + bracket(q["e"])
            + r"^2-\left(\frac{"
            + value(q["b"])
            + r"}{2}\right)^2}="
            + value(q["face"])
        )
        + "<p>Вычислим площадь этого треугольника двумя способами и сократим общий множитель 1/2:</p>"
        + line(base + r"\cdot SH=S" + z + r"\cdot " + height)
        + line(height + r"=\frac{" + base + r"\cdot SH}{S" + z + "}")
        + line(
            height
            + r"=\frac{"
            + bracket(q["b"])
            + r"\cdot "
            + bracket(q["face"])
            + "}{"
            + value(q["e"])
            + "}="
            + value(m.answer)
        )
    )
    return picture(pictures) + parts(proof, calculation)


def _prism(m, pictures):
    q = m.q
    center = m.names[0]
    parent = center == "A"
    other = "B" if parent else "A"
    segment = "A₁B" if parent else "AB₁"
    plane = "AB₁C₁" if parent else "BA₁C₁"
    diagonal = "AB₁" if parent else "BA₁"
    leg = center + other + "_1"
    height = other + "_1H"
    median = center + "M"
    base = other + "_1C_1"
    proof = (
        "<p>Проведём отрезок "
        + segment
        + ". Диагональ "
        + diagonal
        + " прямоугольника ABB₁A₁ лежит в плоскости "
        + plane
        + ". Диагонали прямоугольника делят друг друга пополам, поэтому плоскость "
        + plane
        + " делит "
        + segment
        + " пополам.</p><p>Опустим из концов этого отрезка перпендикуляры на плоскость. Полученные прямоугольные треугольники равны по гипотенузе и острому углу при точке пересечения отрезка с плоскостью. Следовательно, расстояния от его концов до плоскости равны.</p>"
    )
    calculation = (
        "<p>Искомое расстояние равно высоте "
        + other
        + "₁H треугольника "
        + center
        + other
        + "₁C₁. Он равнобедренный: его боковые стороны — равные диагонали прямоугольных граней. Обозначим сторону основания через a, высоту призмы через h. Вычислим боковую сторону и высоту-медиану "
        + median
        + ":</p>"
        + line(leg + r"=\sqrt{a^2+h^2}")
        + line(
            leg
            + r"=\sqrt{"
            + bracket(q["a"])
            + "^2+"
            + bracket(q["H"])
            + "^2}="
            + value(q["leg"])
        )
        + line(
            median + r"=\sqrt{" + leg + r"^2-\left(\frac{" + base + r"}{2}\right)^2}"
        )
        + line(
            median
            + r"=\sqrt{"
            + bracket(q["leg"])
            + r"^2-\left(\frac{"
            + value(q["a"])
            + r"}{2}\right)^2}="
            + value(q["median"])
        )
        + "<p>Найдём площадь треугольника двумя способами — через основание "
        + base.replace("_1", "₁")
        + " и через сторону "
        + leg.replace("_1", "₁")
        + ". После сокращения общего множителя 1/2:</p>"
        + line(base + r"\cdot " + median + "=" + center + r"C_1\cdot " + height)
        + line(height + r"=\frac{" + base + r"\cdot " + median + "}{" + center + "C_1}")
        + line(
            height
            + r"=\frac{"
            + bracket(q["a"])
            + r"\cdot "
            + bracket(q["median"])
            + "}{"
            + value(q["leg"])
            + "}="
            + value(m.answer)
        )
    )
    return picture(pictures) + parts(proof, calculation)


def _square(m, pictures):
    q = m.q
    media = (
        '<section data-layout="media-row" data-layout-align="flex-end">'
        + "".join(
            '<section data-layout="media-item">'
            + pictures.get("image_" + str(i), "")
            + "<p><nobr>Рис. "
            + str(i)
            + "</nobr></p></section>"
            for i in (1, 2)
        )
        + "</section>"
    )
    proof = (
        "<p>Пусть данное сечение — квадрат AA₁ML, где L — середина BC, а O — точка пересечения его диагоналей. Диагонали квадрата перпендикулярны: AM ⟂ A₁L. Проекция AM на плоскость основания — AL, причём AL ⟂ BC. По теореме о трёх перпендикулярах AM ⟂ BC, поэтому AM перпендикулярна плоскости A₁BC.</p><p>Точка O лежит на A₁L, то есть в плоскости A₁BC. Опустим из O перпендикуляр OP на A₁B. Отрезок OP лежит в этой плоскости, поэтому OP ⟂ AM. Значит, OP — общий перпендикуляр прямых A₁B и AM, а его длина равна искомому расстоянию.</p>"
        + media
    )
    calculation = (
        "<p>Сторона квадрата равна высоте правильного треугольника ABC. Найдём сторону квадрата, его диагональ и боковую сторону равнобедренного треугольника A₁BC:</p>"
        + line(
            r"AL=\frac{BC\sqrt{3}}{2}=\frac{"
            + bracket(q["a"])
            + r"\cdot\sqrt{3}}{2}="
            + value(q["H"])
        )
        + line(
            r"A_1L=AL\sqrt{2}="
            + bracket(q["H"])
            + r"\cdot\sqrt{2}="
            + value(q["diagonal"])
        )
        + line(
            r"A_1B=\sqrt{AA_1^2+AB^2}=\sqrt{"
            + bracket(q["H"])
            + "^2+"
            + bracket(q["a"])
            + "^2}="
            + value(q["leg"])
        )
        + line(r"A_1O=\frac{A_1L}{2}=\frac{" + value(q["diagonal"]) + "}{2}")
        + line(r"LB=\frac{BC}{2}=\frac{" + value(q["a"]) + "}{2}")
        + "<p>Прямоугольные треугольники A₁OP и A₁BL подобны по общему углу при A₁. Поэтому:</p>"
        + line(r"OP=\frac{A_1O\cdot LB}{A_1B}=\frac{A_1L\cdot BC}{4A_1B}")
        + line(
            r"OP=\frac{"
            + bracket(q["diagonal"])
            + r"\cdot "
            + bracket(q["a"])
            + r"}{4\cdot "
            + bracket(q["leg"])
            + "}="
            + value(m.answer)
        )
    )
    return parts(proof, calculation)


def render(m, pictures):
    return {
        "tetra_midpoint_distance": _midpoint,
        "hex_vertex_line_distance": _hex,
        "prism_plane_altitude": _prism,
        "prism_square_skew": _square,
    }[m.mode](m, pictures)
