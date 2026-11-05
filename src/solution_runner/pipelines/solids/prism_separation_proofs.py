"""Keep geometric section arguments before the parent's coordinate alternative."""

import sympy as sp

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value
from .spatial_distance_proofs import parts
from .spatial_metric_proofs import picture


def _square_lengths(m):
    q = m.q
    return (
        "<p>Проведём через K и L прямые KK₁ и LL₁, параллельные BD. Они образуют сечение KK₁LL₁. Плоскость AA₁C₁C пересекает эти прямые в точках E и F соответственно. По подобию треугольников в квадратных основаниях:</p>"
        + line(
            r"AC=A_1C_1=AB\sqrt{2}="
            + bracket(q["a"])
            + r"\sqrt{2}="
            + value(q["width"])
        )
        + line(
            r"CE=\frac{CK}{\sqrt{2}}=\frac{"
            + value(q["a"] - q["k"])
            + r"}{\sqrt{2}}="
            + value(q["CE"])
        )
        + line(
            r"C_1F=\frac{C_1L}{\sqrt{2}}=\frac{"
            + value(q["l"])
            + r"}{\sqrt{2}}="
            + value(q["C1F"])
        )
        + line(r"AA_1=" + value(q["H"]))
        + line(r"EF=\sqrt{AA_1^2+(C_1F-CE)^2}")
        + line(
            r"EF=\sqrt{"
            + bracket(q["H"])
            + "^2+("
            + value(q["C1F"])
            + "-"
            + value(q["CE"])
            + ")^2}="
            + value(q["EF"])
        )
    )


def _square_perpendicular(m, pictures):
    q = m.q
    forward = m.names[0] == "AC_1"
    end = "C_1" if forward else "C"
    adjacent = "C_1F" if forward else "CE"
    other = "AE" if forward else "A_1F"
    adjacent_value = q["C1F"] if forward else q["CE"]
    other_value = q["AE"] if forward else q["width"] - q["C1F"]
    ratio = sp.simplify(adjacent_value / (adjacent_value + other_value))
    leg = sp.simplify(q["diagonal"] * ratio)
    small = sp.simplify(q["EF"] * ratio)
    short = "FO" if forward else "EO"
    diagonal = m.names[0]
    first = (
        _square_lengths(m)
        + "<p>Обозначим пересечение EF и диагонали "
        + diagonal.replace("_1", "₁")
        + " через O. "
        + ("Треугольники AEO и C₁FO" if forward else "Треугольники CEO и A₁FO")
        + " подобны по вертикальным углам при O и углам при параллельных основаниях прямоугольника. Поэтому:</p>"
        + line(diagonal + r"=\sqrt{AC^2+AA_1^2}=" + value(q["diagonal"]))
        + line(other + "=" + value(other_value))
        + line(
            end
            + r"O=\frac{"
            + adjacent
            + "}{"
            + adjacent
            + "+"
            + other
            + r"}\cdot "
            + diagonal
        )
        + line(
            end
            + "O="
            + bracket(ratio)
            + r"\cdot "
            + bracket(q["diagonal"])
            + "="
            + value(leg)
        )
        + line(
            short
            + r"=\frac{"
            + adjacent
            + "}{"
            + adjacent
            + "+"
            + other
            + r"}\cdot EF="
            + value(small)
        )
        + line(
            end
            + "O^2+"
            + short
            + "^2="
            + bracket(leg)
            + "^2+"
            + bracket(small)
            + "^2="
            + value(adjacent_value**2)
            + "="
            + adjacent
            + "^2"
        )
        + "<p>По теореме, обратной теореме Пифагора, диагональ "
        + diagonal.replace("_1", "₁")
        + " перпендикулярна EF. Её проекция на основание параллельна AC, а AC ⟂ BD. По теореме о трёх перпендикулярах эта диагональ перпендикулярна и KK₁ ∥ BD. Прямые EF и KK₁ пересекаются в плоскости γ, следовательно, диагональ перпендикулярна γ.</p>"
    )
    if pictures.get("image_2") and m.symbols.get("image2_role") == "section":
        first = pictures["image_2"] + first
    return first, leg, adjacent_value


def square_geometry(m, pictures):
    q = m.q
    forward = m.names[0] == "AC_1"
    end = "C_1" if forward else "C"
    adjacent = "C_1F" if forward else "CE"
    first, leg, adjacent_value = _square_perpendicular(m, pictures)
    projection = "MF" if forward else "NE"
    projection_value = (
        (q["a"] - q["l"]) / sp.sqrt(2) if forward else q["k"] / sp.sqrt(2)
    )
    origin = "M — середина A₁C₁" if forward else "N — точка пересечения AC и BD"
    second = (
        "<p>Прямая "
        + ("B₁D₁" if forward else "BD")
        + " параллельна плоскости γ. Поэтому её точки равноудалены от γ. Пусть "
        + origin
        + ". Опустим из этой точки перпендикуляр на EF в плоскости AA₁C₁C. Он параллелен доказанной нормали к γ и является искомым расстоянием d.</p>"
        + line(
            projection
            + "="
            + (r"\frac{A_1C_1}{2}-C_1F" if forward else r"\frac{AC}{2}-CE")
        )
        + line(projection + "=" + value(projection_value))
        + "<p>По подобию полученного прямоугольного треугольника и треугольника с вершинами "
        + end.replace("_1", "₁")
        + ", O и "
        + ("F" if forward else "E")
        + ":</p>"
        + line(r"d=\frac{" + projection + r"\cdot " + end + "O}{" + adjacent + "}")
        + line(
            r"d=\frac{"
            + bracket(projection_value)
            + r"\cdot "
            + bracket(leg)
            + "}{"
            + value(adjacent_value)
            + "}="
            + value(m.answer)
        )
    )
    return picture(pictures) + parts(first, second)


def _triangle_perpendicular(m, pictures):
    q = m.q
    n, e, f = (
        ("T", "K_3", "L_3")
        if m.symbols.get("section_layout") == "midpoints"
        else ("N", "E", "F")
    )
    ne = n + e
    mf = "M" + f
    gap = q["EP"]
    first = (
        "<p>Через K и L проведём прямые KK₁ и LL₁, параллельные AC. Получим сечение KK₁LL₁. Пусть "
        + n
        + " — середина AC, а "
        + e.replace("_3", "₃")
        + " и "
        + f.replace("_3", "₃")
        + " — середины KK₁ и LL₁. Они лежат в плоскости прямоугольника BB₁M"
        + n
        + ". По подобию треугольников в основаниях:</p>"
        + line("B" + n + r"=B_1M=\frac{AB\sqrt{3}}{2}=" + value(q["width"]))
        + line(
            ne
            + r"=\frac{AK}{AB}\cdot B"
            + n
            + r"=\frac{"
            + value(q["k"])
            + "}{"
            + value(q["a"])
            + r"}\cdot "
            + bracket(q["width"])
            + "="
            + value(q["NE"])
        )
        + line(
            mf
            + r"=\frac{LC_1}{B_1C_1}\cdot B_1M=\frac{"
            + value(q["a"] - q["l"])
            + "}{"
            + value(q["a"])
            + r"}\cdot "
            + bracket(q["width"])
            + "="
            + value(q["MF"])
        )
        + "<p>Горизонтальное смещение между концами отрезка "
        + e.replace("_3", "₃")
        + f.replace("_3", "₃")
        + " равно Δ, а вертикальное — высоте призмы. Обозначим угол этого отрезка с основанием через φ, угол BM с основанием — через ψ:</p>"
        + line(r"\Delta=" + mf + "-" + ne + "=" + value(gap))
        + line(
            r"\tan\varphi=\frac{BB_1}{\Delta}=\frac{"
            + value(q["H"])
            + "}{"
            + value(gap)
            + "}="
            + value(q["H"] / gap)
        )
        + line(
            r"\tan\psi=\frac{BB_1}{B"
            + n
            + r"}=\frac{"
            + value(q["H"])
            + "}{"
            + value(q["width"])
            + "}="
            + value(q["H"] / q["width"])
        )
        + line(
            r"\tan\varphi\tan\psi="
            + bracket(q["H"] / gap)
            + r"\cdot "
            + bracket(q["H"] / q["width"])
            + "=1"
        )
        + "<p>Эти острые углы дополняют друг друга до 90°, поэтому BM перпендикулярна "
        + e.replace("_3", "₃")
        + f.replace("_3", "₃")
        + ". Кроме того, AC ⟂ B"
        + n
        + " и AC ⟂ BB₁, поэтому AC перпендикулярна плоскости BB₁M, значит, BM ⟂ KK₁. Следовательно, BM перпендикулярна плоскости γ.</p>"
    )
    if pictures.get("image_2"):
        first += pictures["image_2"]
    return first, n, e, f


def triangle_geometry(m, pictures):
    q = m.q
    first, n, e, f = _triangle_perpendicular(m, pictures)
    ne = n + e
    gap = q["EP"]
    length = sp.sqrt(q["H"] ** 2 + gap**2)
    second = (
        "<p>Так как AC ∥ γ, искомое расстояние от C равно расстоянию от "
        + n
        + " до γ. В плоскости BB₁M это расстояние до прямой "
        + e.replace("_3", "₃")
        + f.replace("_3", "₃")
        + ". По теореме Пифагора и формуле площади треугольника:</p>"
        + line(
            e
            + f
            + r"=\sqrt{BB_1^2+\Delta^2}=\sqrt{"
            + bracket(q["H"])
            + "^2+"
            + bracket(gap)
            + "^2}="
            + value(length)
        )
        + line(r"d=\frac{" + ne + r"\cdot BB_1}{" + e + f + "}")
        + line(
            r"d=\frac{"
            + bracket(q["NE"])
            + r"\cdot "
            + bracket(q["H"])
            + "}{"
            + value(length)
            + "}="
            + value(m.answer)
        )
    )
    return picture(pictures) + parts(first, second)


def coordinates(m, pictures):
    q = m.q
    triangular = m.mode == "triangle_prism_section_distance"
    if triangular:
        intro = "<p>Поместим начало координат в B, ось Ox направим параллельно AC, ось Oy — по медиане основания, ось Oz — по BB₁. Обозначим высоту основания через v. Тогда A(−a/2, v, 0), C(a/2, v, 0), K(−(a−k)/2, (a−k)v/a, 0), L(l/2, lv/a, h), M(0, v, h), где a = AB, h = BB₁, k = AK, l = B₁L.</p>"
        constant = q["width"] - q["NE"]
        denominator = sp.sqrt(1 + q["normal_z"] ** 2)
        equation = "y+" + bracket(q["normal_z"]) + "z-" + bracket(constant) + "=0"
        vector = r"\overrightarrow{BM}=" + bracket(q["width"]) + r"\vec n"
        numerator = q["NE"]
        formula = r"\frac{\left|v-c\right|}{\sqrt{1+n_z^2}}"
    else:
        intro = "<p>Поместим начало координат в C, оси Ox и Oy направим по CB и CD, ось Oz — по CC₁. Тогда A(a, a, 0), B(a, 0, 0), K(a−k, 0, 0), K₁(0, a−k, 0), L(0, l, h), где a = AB, h = AA₁, k = BK, l = C₁L.</p>"
        constant = q["a"] - q["k"]
        denominator = sp.sqrt(2 + q["normal_z"] ** 2)
        equation = "x+y+" + bracket(q["normal_z"]) + "z-" + bracket(constant) + "=0"
        vector = r"\overrightarrow{" + m.names[0] + "}=-" + bracket(q["a"]) + r"\vec n"
        numerator = q["a"] - q["l"] if m.names[1] == "B_1" else q["k"]
        formula = r"\frac{\left|a+n_z\cdot z_0-c\right|}{\sqrt{2+n_z^2}}"
    normal = "(0; 1; " if triangular else "(1; 1; "
    first = (
        intro
        + "<p>Подставляя координаты точек сечения в уравнение плоскости, получаем:</p>"
        + line(equation)
        + "<p>Нормаль к этой плоскости и направляющий вектор доказываемой прямой коллинеарны:</p>"
        + line(
            r"\vec n=\left"
            + normal.replace(";", ",")
            + value(q["normal_z"])
            + r"\right)"
        )
        + line(vector)
        + "<p>Следовательно, прямая перпендикулярна плоскости γ.</p>"
    )
    if pictures.get("image_2") and m.symbols.get("image2_role") == "coordinate":
        first = pictures["image_2"] + first
    second = (
        "<p>В формуле расстояния от точки до плоскости обозначим свободный член с противоположным знаком через c, третью координату нормали — через n_z. Подставим координаты требуемой вершины:</p>"
        + line("c=" + value(constant))
        + line("n_z=" + value(q["normal_z"]))
        + (
            ""
            if triangular
            else line("z_0=" + value(q["H"] if m.names[1] == "B_1" else 0))
        )
        + line("d=" + formula)
        + line(
            r"d=\frac{"
            + value(numerator)
            + "}{"
            + value(denominator)
            + "}="
            + value(m.answer)
        )
    )
    return parts(first, second)


def render(m, pictures):
    geometric = (
        triangle_geometry
        if m.mode == "triangle_prism_section_distance"
        else square_geometry
    )
    return (
        geometric(m, pictures)
        + "<p><b>Решение векторно-координатным методом.</b></p>"
        + coordinates(m, pictures)
    )
