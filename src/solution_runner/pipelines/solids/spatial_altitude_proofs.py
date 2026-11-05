"""Preserve the parents' altitude, midpoint and volume methods."""

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value
from .spatial_distance_proofs import parts
from .spatial_metric_proofs import picture


def _rectangular_proof(m):
    q = m.q
    return (
        "<p>Проверим равенства в треугольниках ASB и ASD:</p>"
        + line(
            "AB^2+SA^2="
            + bracket(q["a"])
            + "^2+"
            + bracket(q["H"])
            + "^2="
            + value(q["SB"] ** 2)
            + "=SB^2"
        )
        + line(
            "AD^2+SA^2="
            + bracket(q["b"])
            + "^2+"
            + bracket(q["H"])
            + "^2="
            + value(q["SD"] ** 2)
            + "=SD^2"
        )
        + "<p>По теореме, обратной теореме Пифагора, SA ⟂ AB и SA ⟂ AD. Прямые AB и AD пересекаются и лежат в основании. По признаку перпендикулярности прямой и плоскости SA перпендикулярна плоскости ABCD, то есть является высотой пирамиды.</p>"
    )


def rectangular(m, pictures):
    q = m.q
    if m.mode == "rectangular_pyramid_angle":
        second = (
            "<p>В прямоугольнике BC ∥ AD. Поскольку AD ⟂ SA и AD ⟂ AB, прямая BC перпендикулярна плоскости ASB. Поэтому SB — ортогональная проекция SC на эту плоскость, а искомый угол равен ∠CSB. В прямоугольном треугольнике SBC:</p>"
            + line(r"\tan\angle CSB=\frac{BC}{SB}")
            + line(
                r"\tan\angle CSB=\frac{"
                + value(q["b"])
                + "}{"
                + value(q["SB"])
                + "}="
                + value(q["tangent"])
            )
            + line(r"\angle CSB=" + value(m.answer) + r"^{\circ}")
        )
    else:
        second = (
            "<p>Опустим из A перпендикуляр на SB. Прямая BC перпендикулярна плоскости ASB, поскольку BC ⟂ AB и BC ⟂ SA. Поэтому построенный перпендикуляр также перпендикулярен BC, а значит, всей плоскости SBC. Его длина d — искомое расстояние.</p><p>Площадь прямоугольного треугольника ASB выразим через два разных основания:</p>"
            + line(r"2S_{ASB}=SA\cdot AB=SB\cdot d")
            + line(r"d=\frac{SA\cdot AB}{SB}")
            + line(
                r"d=\frac{"
                + bracket(q["H"])
                + r"\cdot "
                + bracket(q["a"])
                + "}{"
                + value(q["SB"])
                + "}="
                + value(m.answer)
            )
        )
    return picture(pictures) + parts(_rectangular_proof(m), second)


def midpoint(m, pictures):
    q = m.q
    target = m.names[0]
    first = "<p>Поскольку BC ∥ AD, плоскость ADM пересекает грань SBC по прямой KM, параллельной BC, где K лежит на SB. Точка M — середина SC, поэтому по теореме о средней линии K — середина SB. Построим сечение ADMK. Оно делит отрезок BS пополам, значит, расстояния от B и S до плоскости ADM равны.</p>"
    segment = "NQ" if target == "B" else "SQ"
    second = (
        "<p>Пусть P — середина AD, N — середина BC. Рассмотрим сечение SNP. В правильной пирамиде SP и SN — равные высоты боковых граней. Найдём их по теореме Пифагора:</p>"
        + line(r"AP=\frac{AD}{2}=\frac{" + value(q["a"]) + "}{2}=" + value(q["a"] / 2))
        + line(r"SN=SP=\sqrt{SA^2-AP^2}")
        + line(
            r"SN=SP=\sqrt{"
            + bracket(q["e"])
            + "^2-"
            + bracket(q["a"] / 2)
            + "^2}="
            + value(q["l"])
        )
        + line("NP=AB=" + value(q["a"]))
        + "<p>Таким образом, треугольник SNP равносторонний. Пусть Q — середина SN; она одновременно является серединой KM, поэтому PQ лежит в плоскости ADM. Медиана PQ является также высотой, поэтому PQ ⟂ SN. Поскольку AD ⟂ NP и AD ⟂ SP, плоскость SNP перпендикулярна AD; следовательно, SN ⟂ AD. Прямая SN перпендикулярна обеим пересекающимся прямым AD и PQ плоскости ADM, а значит, перпендикулярна этой плоскости.</p>"
        + (
            "<p>Так как BC ∥ AD, точки B и N равноудалены от плоскости ADM. Искомое расстояние равно NQ:</p>"
            if target == "B"
            else "<p>Искомое расстояние от S до плоскости ADM равно SQ:</p>"
        )
        + line(
            segment
            + r"=\frac{SN}{2}=\frac{"
            + value(q["l"])
            + "}{2}="
            + value(m.answer)
        )
    )
    return picture(pictures) + parts(first, second)


def _triangle_proof(m):
    if m.names[0] == "perpendicular":
        return "<p>Пусть SO — высота пирамиды. Проекцией AS на плоскость основания является AO. В равностороннем треугольнике ABC центр O лежит на высоте из A, поэтому AO ⟂ BC. По теореме о трёх перпендикулярах AS ⟂ BC.</p>"
    return "<p>Пусть SO и AH — высоты пирамиды, M — середина BC. В равностороннем треугольнике ABC точка O лежит на AM. В равнобедренном треугольнике SBC отрезок SM перпендикулярен BC, поэтому плоскость ASM перпендикулярна BC. Проекция A на плоскость SBC лежит на SM: AH перпендикулярна и SM, и BC. Значит, AH и SO лежат в одной плоскости ASM. Они не параллельны: AH ⟂ SM, а SO не перпендикулярна SM. Следовательно, высоты пересекаются.</p>"


def triangle(m, pictures):
    q = m.q
    volume = q["V"]
    area = q["a"] * q["l"] / 2
    second = (
        "<p>В равностороннем треугольнике ABC найдём AO, а затем высоту SO пирамиды:</p>"
        + line(
            r"AO=\frac{AB}{\sqrt{3}}=\frac{"
            + value(q["a"])
            + r"}{\sqrt{3}}="
            + value(q["R"])
        )
        + line(
            r"SO=\sqrt{SA^2-AO^2}=\sqrt{"
            + bracket(q["e"])
            + "^2-"
            + bracket(q["R"])
            + "^2}="
            + value(q["H"])
        )
        + "<p>Вычислим объём, взяв основанием треугольник ABC:</p>"
        + line(r"V=\frac{1}{3}\cdot SO\cdot\frac{AB^2\sqrt{3}}{4}")
        + line(
            r"V=\frac{1}{3}\cdot "
            + bracket(q["H"])
            + r"\cdot\frac{"
            + bracket(q["a"])
            + r"^2\sqrt{3}}{4}="
            + value(volume)
        )
        + "<p>Теперь примем за основание грань SBC. В равнобедренном треугольнике SBC высота SM делит BC пополам:</p>"
        + line(
            r"SM=\sqrt{SB^2-MB^2}=\sqrt{"
            + bracket(q["e"])
            + r"^2-\left(\frac{"
            + value(q["a"])
            + r"}{2}\right)^2}="
            + value(q["l"])
        )
        + line(
            r"S_{SBC}=\frac{1}{2}\cdot BC\cdot SM=\frac{1}{2}\cdot "
            + bracket(q["a"])
            + r"\cdot "
            + bracket(q["l"])
            + "="
            + value(area)
        )
        + "<p>Высотой к этой грани является искомое расстояние h. Объём пирамиды не изменился:</p>"
        + line(r"V=\frac{1}{3}hS_{SBC}")
        + line(
            r"h=\frac{3V}{S_{SBC}}=\frac{3\cdot "
            + bracket(volume)
            + "}{"
            + value(area)
            + "}="
            + value(m.answer)
        )
    )
    return picture(pictures) + parts(_triangle_proof(m), second)


def render(m, pictures):
    return {
        "rectangular_pyramid_distance": rectangular,
        "rectangular_pyramid_angle": rectangular,
        "square_midplane_distance": midpoint,
        "triangle_face_distance": triangle,
    }[m.mode](m, pictures)
