"""Recover an edge ratio from section area and retain the coordinate proof."""

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value
from .spatial_distance_proofs import parts


def _proof():
    return "<p>Проведём BH — высоту треугольника SBC. Треугольники SBC и SDC равны по трём сторонам, поэтому основание высоты из D на SC — та же точка H. Значит, BH ⟂ SC и DH ⟂ SC. По признаку перпендикулярности прямой и плоскости плоскость BHD перпендикулярна SC. Она содержит диагональ BD и её середину O. Через O проходит единственная плоскость, перпендикулярная SC, следовательно, BHD совпадает с α и содержит B и D.</p>"


def _calculation(m):
    q = m.q
    return (
        "<p>Сечение — равнобедренный треугольник BHD. Его высота OH проходит через середину BD. Выразим её через данную площадь:</p>"
        + line(
            r"BD=AB\sqrt{2}=" + bracket(q["a"]) + r"\sqrt{2}=" + value(q["diagonal"])
        )
        + line(
            r"OH=\frac{2S_{BHD}}{BD}=\frac{2\cdot "
            + bracket(q["area"])
            + "}{"
            + value(q["diagonal"])
            + "}="
            + value(q["OH"])
        )
        + "<p>В квадрате OC равно половине диагонали. Поскольку OH ⟂ SC, треугольник OHC прямоугольный:</p>"
        + line(r"OC=\frac{BD}{2}=" + value(q["OC"]))
        + line(
            r"HC^2=OC^2-OH^2="
            + bracket(q["OC"])
            + "^2-"
            + bracket(q["OH"])
            + "^2="
            + value(q["HC"] ** 2)
        )
        + line("HC=" + value(q["HC"]))
        + "<p>В прямоугольном треугольнике SCO высота OH делит гипотенузу SC. По свойству катета:</p>"
        + line(r"SC\cdot HC=OC^2")
        + line(
            r"SC=\frac{OC^2}{HC}=\frac{"
            + bracket(q["OC"])
            + "^2}{"
            + value(q["HC"])
            + "}="
            + value(q["SC"])
        )
        + line(
            "SH=SC-HC=" + value(q["SC"]) + "-" + bracket(q["HC"]) + "=" + value(q["SH"])
        )
        + line(
            r"\frac{SH}{HC}=\frac{"
            + value(q["SH"])
            + "}{"
            + value(q["HC"])
            + "}="
            + value(m.answer)
        )
    )


def _coordinate(m, pictures):
    a = value(m.q["a"])
    half = value(m.q["a"] / 2)
    slot = m.symbols.get("coordinate_slot", "")
    return (
        "<p><b>Другой способ доказательства пункта а).</b></p>"
        + pictures.get(slot, "")
        + "<p>Начало координат выберем в D, оси x и y направим вдоль DA и DC, а ось z — параллельно высоте SO. Обозначим SO через h. Тогда:</p>"
        + line(
            "D(0;0;0),\\quad A("
            + a
            + ";0;0),\\quad C(0;"
            + a
            + ";0),\\quad B("
            + a
            + ";"
            + a
            + ";0)"
        )
        + line("O(" + half + ";" + half + ";0),\\quad S(" + half + ";" + half + ";h)")
        + line(r"\overrightarrow{SC}=(-" + half + ";" + half + ";-h)")
        + "<p>Этот вектор — нормаль к α. Подставляя координаты O, получаем нулевой свободный член. Поэтому уравнение плоскости:</p>"
        + line(
            "-"
            + bracket(m.q["a"] / 2)
            + r"x+"
            + bracket(m.q["a"] / 2)
            + r"y-h\cdot z=0"
        )
        + "<p>Координаты D и B удовлетворяют этому уравнению: у D все координаты нулевые, а у B первые два слагаемых взаимно уничтожаются. Следовательно, обе вершины принадлежат α.</p>"
    )


def render(m, pictures):
    return (
        pictures.get(m.symbols.get("main_slot", "image_1"), "")
        + parts(_proof(), _calculation(m))
        + _coordinate(m, pictures)
    )
