"""Parent-style squaring, exact unit conversions and minimum integer ascent."""

import sympy as sp

from ..calculus.common import answer
from ..probability.common import line

_UNIT_NOTE = "<p>Примечание. Радиус Земли и расстояние до горизонта в этой формуле выражены в километрах, высота — в метрах. За согласование единиц отвечает коэффициент 500. При одинаковых единицах длины формула имеет вид:</p>"


def final(a, minimum=False):
    q = a.question
    unit = {
        r"км/ч^{2}": r"\mathrm{км}/\mathrm{ч}^{2}",
        r"м/с^{2}": r"\mathrm{м}/\mathrm{с}^{2}",
    }.get(q.unit, r"\text{" + q.unit + "}")
    label = q.label + (r"_{\min}" if minimum else "")
    decimal = answer(a.result).replace(",", "{,}")
    return line(
        label
        + "="
        + sp.latex(a.result)
        + ("=" + decimal if a.result.is_Integer is not True else "")
        + r"\ "
        + unit
    )


def motion(a):
    q = a.question
    v = q.values
    relation = r"\geq" if q.relation == "ge" else "="
    html = line(r"v=\sqrt{2la}")
    if q.kind == "root_distance":
        html += line(r"v^2=2la")
        native = v["speed"] ** 2 / (2 * v["acceleration"])
        try:
            native_decimal = answer(native).replace(",", "{,}") if native.is_Integer is not True else ""
        except ValueError:
            native_decimal = ""
        html += line(
            r"l=\frac{v^2}{2a}=\frac{"
            + sp.latex(v["speed"])
            + r"^2}{2\cdot"
            + sp.latex(v["acceleration"])
            + "}="
            + sp.latex(native)
            + ("=" + native_decimal if native_decimal else "")
            + r"\ \text{" + v["native_unit"] + "}"
        )
        if v["native_unit"] != q.unit:
            html += "<p>По единицам скорости и ускорения путь получен в исходных единицах. Переведём его в единицы ответа:</p>"
            html += line("l=" + sp.latex(native) + r"\ \text{" + v["native_unit"] + "}")
            html += line(
                "l="
                + sp.latex(native)
                + r"\cdot"
                + sp.latex(
                    sp.Rational(1, 1000)
                    if v["native_unit"] == "м"
                    else sp.Integer(1000)
                )
                + r"\ \text{"
                + q.unit
                + "}"
            )
            html += final(a)
        return html
    else:
        if v["path"] != v["native_path"]:
            html += line(
            "l="
            + (
                sp.latex(v["path"])
                + r"\cdot"
                + sp.latex(v["native_path"] / v["path"])
                + "="
                if v["path"] != v["native_path"]
                else ""
            )
            + sp.latex(v["native_path"])
            + r"\ \text{"
            + v["native_unit"]
            + "}"
        )
        html += line(r"\sqrt{2\cdot" + sp.latex(v["native_path"]) + r"\cdot a}" + relation + sp.latex(v["speed"]))
        html += line("2\\cdot" + sp.latex(v["native_path"]) + r"\cdot a" + relation + sp.latex(v["speed"]) + "^2")
        html += line(
            "2\\cdot"
            + sp.latex(v["native_path"])
            + "a"
            + relation
            + sp.latex(v["speed"])
            + "^2"
        )
        html += line(
            "a"
            + relation
            + r"\frac{"
            + sp.latex(v["speed"] ** 2)
            + r"}{2\cdot"
            + sp.latex(v["native_path"])
            + "}"
        )
        if q.relation == "ge":
            html += "<p>При большем ускорении скорость в конце того же пути будет больше. Граничное значение допускается условием.</p>"
    return html + final(a, q.relation == "ge")


def horizon(a):
    q = a.question
    v = q.values
    km = q.kind == "root_horizon_km"
    coefficient = 2 * v["radius"] if km else v["radius"] / 500
    html = ""
    html += line(r"l=\sqrt{2Rh}" if km else r"l=\sqrt{\frac{Rh}{500}}")
    html += line("l^2=" + ("2Rh" if km else r"\frac{Rh}{500}"))
    html += line(sp.latex(v["target"]) + "^2=" + sp.latex(coefficient) + "h")
    h_line = (r"h=\frac{" + sp.latex(v["target"]) + r"\cdot" + sp.latex(v["target"]) + "}{" + sp.latex(coefficient) + "}=" + sp.latex(a.result))
    if a.result.is_Integer is not True:
        h_line += "=" + answer(a.result).replace(",", "{,}")
    html += line(h_line + r"\ \text{" + q.unit + "}")
    if km:
        html += "<p>Примечание. Переведём найденную высоту в метры. При наблюдении человеком высоту отсчитывают до уровня глаз:</p>"
        html += line(
            "h="
            + sp.latex(a.result)
            + r"\cdot1000="
            + sp.latex(1000 * a.result)
            + r"\ \text{м}"
        )
    return html


def steps(a):
    v = a.question.values
    initial = v["initial_height"]
    needed = 500 * v["target"] ** 2 / v["radius"]
    rise = max(needed - initial, 0)
    html = _heights(v)
    if needed <= initial:
        return html + "<p>Требуемая дальность уже достигнута, подниматься не нужно.</p>" + final(a, True)
    html += line(r"\Delta h=h_2-h_1=" + sp.latex(needed) + "-" + sp.latex(initial) + "=" + sp.latex(rise) + r"\ \text{м}")
    def exact_text(number):
        try:
            return answer(number).replace(",", "{,}")
        except ValueError:
            return sp.latex(number)

    step = exact_text(v["step_m"])
    rise_text = exact_text(rise)
    quotient = sp.simplify(rise / v["step_m"])
    quotient_text = sp.latex(quotient)
    if not quotient.is_Integer:
        decimal = f"{float(quotient):.3f}".rstrip("0").rstrip(".").replace(".", "{,}")
        quotient_text += r"\approx " + decimal
    html += line(r"h_{\text{ступеньки}}=" + sp.latex(v["step"]) + r"\ \text{см}=" + step + r"\ \text{м}")
    html += line(r"\frac{\Delta h}{h_{\text{ступеньки}}}=\frac{" + rise_text + "}{" + step + "}=" + quotient_text)
    html += "<p>Количество ступенек должно быть целым, поэтому берём ближайшее целое не меньше полученного числа.</p>"
    html += final(a, True)
    return html


def rocket(a):
    q = a.question
    v = q.values
    html = line(r"0\leq v<c=" + sp.latex(v["light"]))
    if v["target"] >= v["length"]:
        html += "<p>Исходная длина уже не превышает заданного предела, поэтому допустима нулевая скорость.</p>"
        html += line(sp.latex(v["length"]) + r"\leq" + sp.latex(v["target"]))
        return html + final(a, True)
    ratio = v["light"] ** 2 * (1 - (v["target"] / v["length"]) ** 2)
    html += line(
        sp.latex(v["length"])
        + r"\sqrt{1-\frac{v^2}{("
        + sp.latex(v["light"])
        + ")^2}}="
        + sp.latex(v["target"])
        + r"\iff \sqrt{1-\frac{v^2}{"
        + sp.latex(v["light"] ** 2)
        + r"}}=\frac{" + sp.latex(v["target"]) + "}{" + sp.latex(v["length"]) + "}"
        + r"\iff 1-\frac{v^2}{"
        + sp.latex(v["light"] ** 2)
        + r"}=\left(\frac{" + sp.latex(v["target"]) + "}{" + sp.latex(v["length"]) + r"}\right)^2"
        + r"\iff 1-\frac{v^2}{"
        + sp.latex(v["light"] ** 2)
        + "}="
        + sp.latex((v["target"] / v["length"]) ** 2)
        + r"\iff \frac{v^2}{" + sp.latex(v["light"] ** 2) + "}="
        + sp.latex(1 - (v["target"] / v["length"]) ** 2)
        + r"\iff v^2=" + sp.latex(ratio)
        + r"\iff v=" + sp.latex(a.result)
    )
    return html


def _heights(v):
    initial = v["initial_height"]
    needed = 500 * v["target"] ** 2 / v["radius"]
    html = "<p>Найдём высоту для каждого из двух расстояний до горизонта. Обе части формулы неотрицательны, поэтому можно возвести их в квадрат:</p>"
    html += line(r"l=\sqrt{\frac{Rh}{500}}\quad\Longrightarrow\quad h=\frac{500l^2}{R}")
    for label, distance, height in [
        ("h_1", v["before"], initial),
        ("h_2", v["target"], needed),
    ]:
        html += line(
            label
            + r"=\frac{500\cdot("
            + sp.latex(distance)
            + ")^2}{"
            + sp.latex(v["radius"])
            + "}="
            + sp.latex(height)
            + r"\ \text{м}"
        )
    return html


def rise(a):
    v = a.question.values
    initial = v["initial_height"]
    needed = 500 * v["target"] ** 2 / v["radius"]
    return (_heights(v)
        + "<p>Чтобы видеть горизонт дальше, нужно подняться на разность найденных высот:</p>"
        + line(r"\Delta h=h_2-h_1=" + sp.latex(needed) + "-" + sp.latex(initial) + "=" + sp.latex(a.result) + r"\ \text{м}"))


PROOFS = {
    "root_acceleration": motion,
    "root_acceleration_min": motion,
    "root_distance": motion,
    "root_horizon": horizon,
    "root_horizon_km": horizon,
    "root_steps": steps,
    "rocket": rocket,
    "rocket_equal": rocket,
    "root_rise": rise,
}
