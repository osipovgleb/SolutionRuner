"""Parent similar triangles and the children's three-figure coincidence proof."""

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value
from .spatial_distance_proofs import parts
from .spatial_metric_proofs import picture


def _intersection(m):
    q = m.q
    ratio = q["fraction"] / (2 - q["fraction"])
    return (
        "<p>Проведём KL перпендикулярно плоскости ABC. Так как α перпендикулярна основанию и содержит K, прямая KL лежит в α. Поэтому α пересекает основание по ML. Обозначим ML ∩ BC через N, а ML ∩ DC через H. Пусть SO — высота пирамиды; O — центр квадрата ABCD. Треугольники SOB и KLB подобны по двум углам:</p>"
        + line(
            r"\frac{BK}{KS}=\frac{BL}{LO}=\frac{"
            + value(q["BK"])
            + "}{"
            + value(q["SK"])
            + "}="
            + value(q["BK"] / q["SK"])
        )
        + line(r"\frac{BL}{LD}=\frac{BK}{2SB-BK}=\frac{BK}{SB+SK}")
        + line(
            r"\frac{BL}{LD}=\frac{"
            + value(q["BK"])
            + "}{"
            + value(q["e"] + q["SK"])
            + "}="
            + value(ratio)
        )
        + "<p>Треугольники MBL и HDL также подобны: MB ∥ DH, а BL и DL лежат на одной прямой. Следовательно:</p>"
        + line(r"\frac{MB}{DH}=\frac{BL}{LD}=" + value(ratio))
        + line(
            r"DH=\frac{LD}{BL}\cdot MB="
            + bracket(1 / ratio)
            + r"\cdot "
            + bracket(q["BM"])
            + "="
            + value(q["a"])
        )
        + "<p>Получили DH = DC. Точки H и C лежат на одном луче DC, значит, H = C. Тогда и N = C, поэтому C принадлежит α.</p>"
    )


def _coincidence(m, pictures):
    q = m.q
    media = (
        '<section data-layout="media-row">'
        + "".join(
            '<section data-layout="media-item">'
            + pictures["image_" + str(i)]
            + "<p><nobr>Рис. "
            + str(i)
            + "</nobr></p></section>"
            for i in (1, 2, 3)
        )
        + "</section>"
    )
    return (
        "<p>Пусть BD пересекает α в точке H (рис. 1), а SO — высота пирамиды. Центр квадрата O лежит на BD. Поэтому плоскость SBD перпендикулярна основанию (рис. 2). Она и α содержат прямую через K, перпендикулярную основанию; их линия пересечения KH перпендикулярна основанию и параллельна SO. В треугольнике SOB:</p>"
        + line(r"BH=\frac{KB}{SB}\cdot OB=\frac{KB}{SB}\cdot\frac{BD}{2}")
        + line(
            r"\frac{BH}{BD}=\frac{"
            + value(q["BK"])
            + r"}{2\cdot "
            + bracket(q["e"])
            + "}="
            + value(q["fraction"] / 2)
        )
        + "<p>Рассмотрим квадрат ABCD (рис. 3). Пусть H₁ — пересечение CM и BD. Треугольники MH₁B и CH₁D подобны по двум углам, поскольку BM ∥ CD:</p>"
        + line(
            r"\frac{BH_1}{DH_1}=\frac{BM}{CD}=\frac{"
            + value(q["BM"])
            + "}{"
            + value(q["a"])
            + "}"
        )
        + line(
            r"\frac{BH_1}{BD}=\frac{BM}{BM+CD}=\frac{"
            + value(q["BM"])
            + "}{"
            + value(q["BM"] + q["a"])
            + "}="
            + value(q["fraction"] / 2)
        )
        + "<p>Таким образом, BH = BH₁. Обе точки лежат на отрезке BD, значит, H = H₁. Прямая MH совпадает с MC и лежит в α, поэтому C принадлежит α.</p>"
        + media
    )


def _area(m, foot, radius):
    q = m.q
    height = "K" + foot
    return (
        "<p>Искомое сечение — треугольник MKC. Найдём высоту пирамиды. В квадрате ABCD:</p>"
        + line(
            radius
            + r"=\frac{BD}{2}=\frac{AB\sqrt{2}}{2}=\frac{"
            + bracket(q["a"])
            + r"\sqrt{2}}{2}="
            + value(q["R"])
        )
        + "<p>По теореме Пифагора и подобию треугольников SOB и K"
        + foot
        + "B:</p>"
        + line(
            r"SO=\sqrt{SB^2-OB^2}=\sqrt{"
            + bracket(q["e"])
            + "^2-"
            + bracket(q["R"])
            + "^2}="
            + value(q["H"])
        )
        + line(
            height
            + r"=\frac{KB}{SB}\cdot SO=\frac{"
            + value(q["BK"])
            + "}{"
            + value(q["e"])
            + r"}\cdot "
            + bracket(q["H"])
            + "="
            + value(q["section_height"])
        )
        + "<p>В прямоугольном треугольнике MBC:</p>"
        + line(
            r"BM=AB-AM=" + value(q["a"]) + "-" + bracket(q["AM"]) + "=" + value(q["BM"])
        )
        + line(
            r"MC=\sqrt{BC^2+BM^2}=\sqrt{"
            + bracket(q["a"])
            + "^2+"
            + bracket(q["BM"])
            + "^2}="
            + value(q["section_base"])
        )
        + "<p>Отрезок "
        + height
        + " перпендикулярен основанию, а значит, и MC. Его основание лежит на MC, поэтому это высота треугольника MKC:</p>"
        + line(r"S_{MKC}=\frac{1}{2} MC\cdot " + height)
        + line(
            r"S_{MKC}=\frac{1}{2}\cdot "
            + bracket(q["section_base"])
            + r"\cdot "
            + bracket(q["section_height"])
            + "="
            + value(m.answer)
        )
    )


def render(m, pictures):
    if m.symbols.get("method") == "coincident_feet":
        return parts(_coincidence(m, pictures), _area(m, "H", "OB"))
    return picture(pictures) + parts(_intersection(m), _area(m, "L", "CO"))
