"""Keep the parent's proportional, base-area and numbered volume-difference methods."""

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value


def _section(title, body):
    return (
        '<section data-content-kind="solution" data-solution-title="'
        + title
        + '">'
        + body
        + "</section>"
    )


def render(m):
    volume, low, high = m.given
    delta = high - low
    proportional = (
        "<p>Объём полностью погружённой детали равен объёму вытесненной ею жидкости. Уровень воды поднялся на:</p>"
        + line(r"\Delta h=h_1-h_0")
        + line(r"\Delta h=" + value(high) + "-" + value(low) + "=" + value(delta))
        + "<p>В призматическом сосуде объём пропорционален высоте. Поэтому объём вытесненной жидкости составляет следующую долю исходного объёма:</p>"
        + line(r"k=\frac{\Delta h}{h_0}")
        + line(r"k=\frac{" + value(delta) + "}{" + value(low) + "}=" + value(m.ratio))
        + line("V_d=kV_0")
        + line(
            "V_d="
            + bracket(m.ratio)
            + r"\cdot"
            + bracket(volume)
            + "="
            + value(m.answer)
        )
    )
    base = (
        "<p>Из формулы объёма призмы найдём площадь основания сосуда:</p>"
        + line("V_0=Bh_0")
        + line(r"B=\frac{V_0}{h_0}")
        + line(r"B=\frac{" + value(volume) + "}{" + value(low) + "}=" + value(m.area))
        + "<p>Объём детали равен объёму вытесненной жидкости, то есть произведению площади основания на приращение уровня воды:</p>"
        + line("V_d=B(h_1-h_0)")
        + line(
            "V_d=" + bracket(m.area) + r"\cdot(" + value(high) + "-" + value(low) + ")"
        )
        + line(
            "V_d=" + bracket(m.area) + r"\cdot" + bracket(delta) + "=" + value(m.answer)
        )
    )
    numbered = (
        '<ol data-layout="source-numbered"><li>Найдём площадь основания сосуда:'
        + line(r"B=\frac{V_0}{h_0}")
        + line(r"B=\frac{" + value(volume) + "}{" + value(low) + "}=" + value(m.area))
        + "</li><li>Найдём суммарный объём воды и погружённой детали:"
        + line("V_1=Bh_1")
        + line(
            "V_1="
            + bracket(m.area)
            + r"\cdot"
            + bracket(high)
            + "="
            + value(m.area * high)
        )
        + "</li><li>Разность суммарного и начального объёмов равна объёму детали:"
        + line("V_d=V_1-V_0")
        + line(
            "V_d=" + value(m.area * high) + "-" + value(volume) + "=" + value(m.answer)
        )
        + "</li></ol>"
    )
    return (
        _section("Решение", proportional)
        + _section("Альтернативное решение.", base)
        + _section("Альтернативное решение.", numbered)
    )
