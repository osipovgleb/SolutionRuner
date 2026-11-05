"""Use the parents' right triangles, apothems and base-area volume formulas."""

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value


def _mul(*args):
    return r"\cdot".join(bracket(a) for a in args)


def _volume(q):
    return (
        "<p>Объём пирамиды равен трети произведения площади основания на высоту:</p>"
        + line(r"V=\frac{1}{3}BH")
        + line(r"V=\frac{1}{3}\cdot" + _mul(q["B"], q["H"]) + "=" + value(q["V"]))
    )


def named(m):
    q = m.q
    target = m.names[2]
    edge = next((n for n in m.names if n.startswith("S") and n != "SO"), "SC")
    radius = "O" + edge[-1]
    opening = (
        "<p>В правильной пирамиде SO — высота, поскольку вершина проецируется в центр основания. Все боковые рёбра равны; расстояния от центра квадрата до его вершин также равны. Рассмотрим прямоугольный треугольник SO"
        + edge[-1]
        + ":</p>"
    )
    rows = (
        opening
        + line("e=" + edge)
        + line("R=" + radius)
        + line("AC=BD=2R")
        + line("e^2=H^2+R^2")
        + "<p>Используем теорему Пифагора и равенство диагоналей квадрата:</p>"
    )
    if m.kind == "named_diagonal":
        return (
            rows
            + line("R^2=e^2-H^2")
            + line(
                r"R=\sqrt{"
                + bracket(q["e"])
                + "^2-"
                + bracket(q["H"])
                + "^2}="
                + value(q["R"])
            )
            + line(target + "=2R")
            + line(target + r"=2\cdot" + bracket(q["R"]) + "=" + value(m.answer))
        )
    if m.kind == "named_height":
        return (
            rows
            + line(r"R=\frac{D}{2}=\frac{" + value(q["D"]) + "}{2}=" + value(q["R"]))
            + line("H^2=e^2-R^2")
            + line(
                r"SO=\sqrt{"
                + bracket(q["e"])
                + "^2-"
                + bracket(q["R"])
                + "^2}="
                + value(m.answer)
            )
        )
    return (
        rows
        + line(r"R=\frac{D}{2}=\frac{" + value(q["D"]) + "}{2}=" + value(q["R"]))
        + line(r"e=\sqrt{H^2+R^2}")
        + line(
            target
            + r"=\sqrt{"
            + bracket(q["H"])
            + "^2+"
            + bracket(q["R"])
            + "^2}="
            + value(m.answer)
        )
    )


def surface(m, apothem):
    q = m.q
    a = q["a"]
    l = q["l"]
    e = q["e"]
    h = q["H"]
    total = m.kind in {"square_total_edge", "square_total_height"}
    from_edge = m.kind.endswith("_edge")
    rows = (
        "<p>Высота боковой грани правильной пирамиды является апофемой. Обозначим её "
        + apothem
        + ". По теореме Пифагора:</p>"
    )
    if from_edge:
        rows += line(apothem + r"^2=e^2-\left(\frac{a}{2}\right)^2") + line(
            apothem
            + r"=\sqrt{"
            + bracket(e)
            + "^2-"
            + bracket(a / 2)
            + "^2}="
            + value(l)
        )
    else:
        rows += line(apothem + r"^2=H^2+\left(\frac{a}{2}\right)^2") + line(
            apothem
            + r"=\sqrt{"
            + bracket(h)
            + "^2+"
            + bracket(a / 2)
            + "^2}="
            + value(l)
        )
    if m.kind == "square_total_edge":
        return (
            rows
            + line("p=2a=" + value(q["P"] / 2))
            + line("B=a^2=" + value(q["B"]))
            + "<p>Полная площадь поверхности — сумма площади основания и боковой поверхности, равной произведению полупериметра на апофему:</p>"
            + line("S=p" + apothem + "+B")
            + line(
                "S="
                + _mul(q["P"] / 2, l)
                + "+"
                + bracket(q["B"])
                + "="
                + value(m.answer)
            )
        )
    if total:
        return (
            rows
            + "<p>Площадь поверхности складывается из площади основания и площадей четырёх боковых граней:</p>"
            + line(r"A=\frac{1}{2}a" + apothem)
            + line(r"A=\frac{1}{2}\cdot" + _mul(a, l) + "=" + value(a * l / 2))
            + line("B=a^2=" + value(q["B"]))
            + line("S=B+4A")
            + line(
                "S="
                + bracket(q["B"])
                + r"+4\cdot"
                + bracket(a * l / 2)
                + "="
                + value(m.answer)
            )
            + "<p><b>Примечание.</b> Площадь боковой поверхности правильной пирамиды равна произведению полупериметра основания на апофему:</p>"
            + line("L=p" + apothem)
        )
    return (
        rows
        + "<p>Площадь боковой поверхности равна половине произведения периметра основания на апофему:</p>"
        + line("P=" + str(6 if m.body == "hexagon" else 4) + "a=" + value(q["P"]))
        + line(r"L=\frac{1}{2}P" + apothem)
        + line(r"L=\frac{1}{2}\cdot" + _mul(q["P"], l))
        + line("L=" + value(m.answer))
    )


def _square_volume(m):
    q = m.q
    if m.kind == "square_volume_height_edge":
        return (
            "<p>В основании лежит квадрат. Его центр O является основанием высоты. По теореме Пифагора найдём расстояние R от центра до вершины основания:</p>"
            + line("R^2=e^2-H^2")
            + line(
                r"R=\sqrt{"
                + bracket(q["e"])
                + "^2-"
                + bracket(q["H"])
                + "^2}="
                + value(q["R"])
            )
            + line("D=2R")
            + "<p>Площадь квадрата равна половине квадрата его диагонали:</p>"
            + line(r"B=\frac{D^2}{2}")
            + line(r"B=\frac{" + bracket(q["D"]) + "^2}{2}=" + value(q["B"]))
            + _volume(q)
        )
    return (
        "<p>В основании лежит квадрат. Его диагонали взаимно перпендикулярны, поэтому расстояние от центра до вершины основания равно стороне, делённой на √2:</p>"
        + line(r"R=\frac{a}{\sqrt{2}}")
        + line(r"R=\frac{" + bracket(q["a"]) + r"}{\sqrt{2}}=" + value(q["R"]))
        + "<p>Высота и расстояние R — катеты прямоугольного треугольника с гипотенузой, равной боковому ребру:</p>"
        + line("H^2=e^2-R^2")
        + line(
            r"H=\sqrt{"
            + bracket(q["e"])
            + "^2-"
            + bracket(q["R"])
            + "^2}="
            + value(q["H"])
        )
        + line("B=a^2=" + value(q["B"]))
        + _volume(q)
    )


def _square_edge(m):
    q = m.q
    return (
        "<p>Из формулы объёма пирамиды выразим площадь квадратного основания. Затем найдём сторону и диагональ квадрата:</p>"
        + line(r"V=\frac{1}{3}BH")
        + line(r"B=\frac{3V}{H}")
        + line(
            r"B=\frac{3\cdot"
            + bracket(q["V"])
            + "}{"
            + bracket(q["H"])
            + "}="
            + value(q["B"])
        )
        + line(r"a=\sqrt{B}=\sqrt{" + bracket(q["B"]) + "}=" + value(q["a"]))
        + line(r"D=a\sqrt{2}=" + value(q["D"]))
        + "<p>Боковое ребро — гипотенуза прямоугольного треугольника, катеты которого равны высоте и половине диагонали основания:</p>"
        + line(r"e^2=H^2+\left(\frac{D}{2}\right)^2")
        + line(
            r"e=\sqrt{"
            + bracket(q["H"])
            + "^2+"
            + bracket(q["D"] / 2)
            + "^2}="
            + value(m.answer)
        )
    )


def _hex(m):
    q = m.q
    base = line(r"B=\frac{3\sqrt{3}}{2}a^2") + line(
        r"B=\frac{3\sqrt{3}}{2}\cdot" + bracket(q["a"]) + "^2=" + value(q["B"])
    )
    if m.kind == "hex_edge":
        return (
            "<p>Основание — правильный шестиугольник. Найдём его площадь и выразим высоту из формулы объёма пирамиды:</p>"
            + base
            + line(r"H=\frac{3V}{B}")
            + line(
                r"H=\frac{3\cdot"
                + bracket(q["V"])
                + "}{"
                + bracket(q["B"])
                + "}="
                + value(q["H"])
            )
            + "<p>Сторона правильного шестиугольника равна радиусу описанной окружности. По теореме Пифагора:</p>"
            + line("R=a")
            + line("e^2=H^2+R^2")
            + line(
                r"e=\sqrt{"
                + bracket(q["H"])
                + "^2+"
                + bracket(q["a"])
                + "^2}="
                + value(m.answer)
            )
        )
    if m.kind == "hex_face_angle":
        angle = q["alpha"]
        rows = (
            "<p>Вершина правильной пирамиды проецируется в центр основания. Расстояние от центра шестиугольника до его стороны равно радиусу вписанной окружности r:</p>"
            + line(r"\alpha=" + value(angle) + r"^{\circ}")
            + line(r"r=\frac{\sqrt{3}}{2}a")
            + line(r"r=\frac{\sqrt{3}}{2}\cdot" + bracket(q["a"]) + "=" + value(q["r"]))
            + "<p>В прямоугольном треугольнике с высотой пирамиды угол между апофемой и её проекцией равен двугранному углу. Поэтому:</p>"
            + line(r"H=r\tan\alpha")
            + line("H=" + value(q["H"]))
        )
        return rows + base + _volume(q)
    return (
        "<p>Сторона правильного шестиугольника равна радиусу описанной окружности. Высоту пирамиды найдём по теореме Пифагора:</p>"
        + line("R=a")
        + line("H^2=e^2-R^2")
        + line(
            r"H=\sqrt{"
            + bracket(q["e"])
            + "^2-"
            + bracket(q["a"])
            + "^2}="
            + value(q["H"])
        )
        + "<p>Найдём площадь правильного шестиугольника в основании:</p>"
        + base
        + _volume(q)
    )


def _perpendicular(m):
    q = m.q
    if m.kind == "perpendicular":
        return (
            "<p>Считаем прямоугольный треугольник ASB основанием пирамиды. Ребро SC перпендикулярно двум его сторонам, поэтому перпендикулярно всей плоскости и является высотой:</p>"
            + line(r"B=\frac{1}{2}a^2")
            + line(r"B=\frac{1}{2}\cdot" + bracket(q["a"]) + "^2=" + value(q["B"]))
            + line("H=a=" + value(q["a"]))
            + _volume(q)
        )
    return (
        "<p>Высота H опускается на сторону основания, лежащую в перпендикулярной грани. Эта грань является равносторонним треугольником. Обозначим длину её основания x, а соседнюю сторону прямоугольника y:</p>"
        + line("H=" + value(q["H"]))
        + line(r"x=\frac{2H}{\sqrt{3}}")
        + line(r"x=\frac{2\cdot" + bracket(q["H"]) + r"}{\sqrt{3}}=" + value(q["x"]))
        + "<p>В сечении через высоту и середину противоположной стороны используем угол 60°. Затем найдём площадь прямоугольника:</p>"
        + line(r"y=H\cot60^{\circ}=\frac{H}{\sqrt{3}}")
        + line(r"y=\frac{" + bracket(q["H"]) + r"}{\sqrt{3}}=" + value(q["y"]))
        + line("B=xy")
        + line("B=" + _mul(q["x"], q["y"]) + "=" + value(q["B"]))
        + _volume(q)
    )


def render(m, apothem="l"):
    if m.kind.startswith("named_"):
        return named(m)
    if m.kind in {
        "square_total_edge",
        "square_total_height",
        "hex_lateral_edge",
        "square_lateral_height",
    }:
        return surface(m, apothem)
    if m.kind.startswith("perpendicular"):
        return _perpendicular(m)
    if m.kind.startswith("hex_"):
        return _hex(m)
    if m.kind == "square_edge":
        return _square_edge(m)
    return _square_volume(m)
