"""Render the reviewed side-altitude arguments with their original method order."""

import hashlib

import sympy as sp

from ...core.errors import ContentPlanError
from ...probability.common import line
from ..right.altitude_methods import solution_section
from ..right.altitude_parent import exact_answer

_PARENTS = {
    "isosceles-triangle-27320-altitude-from-base-sine": "0ac5e2a71066486129b1300b181c3d95762292927671bc612ef4146c82af7705",
    "isosceles-triangle-27321-projection-from-base-sine": "91a45789be509525f4bf990a7887d439ae97799052631545dcc1084a3413527d",
    "isosceles-triangle-27322-altitude-from-base-cosine": "b3e83ae53b70b177d6c860b580077474db1ab4d7fd588149bf2d221f7b3a81e1",
    "isosceles-triangle-27323-projection-from-base-cosine": "6ad1771df1bca226c60a14c829e1a6dbb623a06f88a120cc9b5ef784fb07d20d",
    "isosceles-triangle-27324-altitude-from-base-tangent": "dbe332907c5299b956d2fdfccb2745d1f31e3cf2c8c545582196c2f3b368948c",
    "isosceles-triangle-27325-projection-from-base-tangent": "a9d915fc46c1e04bb3635c30f3b40af21aa8a91740985d955129b149e85f96a1",
    "isosceles-triangle-27326-altitude-from-side-sine": "004a36fdac057beca6a777292547ee2fd6a34e6fcd7f19f7922d3cb9f7ef7b27",
    "isosceles-triangle-27327-projection-from-side-sine": "966bf1129fbc7d6605965575127e5902a2abcdff2c88e5cd332343e6143ed35c",
    "isosceles-triangle-27328-altitude-from-side-cosine": "045d87f0811920f13a2dabbb5a68b9a863889480a53605efa7b923af712d7d1a",
    "isosceles-triangle-27329-projection-from-side-cosine": "93ed21af90d03b2002d7f4e97ee6a719c93a9dd7b8446b6a1b78c03cc883ab61",
    "isosceles-triangle-27330-sine-from-altitude-and-base": "f369de7df78d832b335c4ac93d05608a89e18cb13a4b5266efd7ce1e35746c48",
    "isosceles-triangle-27331-cosine-from-altitude-and-base": "b77d50d52a03a5b349e7bee31d066563a4868d89eaf3607dec558ee77ff4615a",
}


def review_parent(html, rule):
    if not isinstance(html, str) or hashlib.sha256(
        html.encode()
    ).hexdigest() != _PARENTS.get(rule):
        raise ContentPlanError(
            "the complete side-altitude parent methods must be reviewed"
        )


def number(value):
    return sp.latex(sp.simplify(value)).replace(r" \sqrt", r"\sqrt")


def angle(model):
    return model.other_base_vertex + model.vertex + model.apex


def trig(function, vertex_angle):
    return "\\" + function + r"\angle " + vertex_angle


def intro(model):
    p, q, r = model.vertex, model.other_base_vertex, model.apex
    text = f"<p>Треугольник ABC — равнобедренный, поэтому углы {q + p + r} и {p + q + 'H'} равны как углы при основании. Высота {p + 'H'} проведена к прямой {q + r}. "
    if model.topology > 0:
        text += f"Ее основание H лежит на продолжении стороны {q + r} за точку {r}. "
    elif model.topology == 0:
        text += f"Ее основание H совпадает с вершиной {r}. "
    return (
        text + "Тогда:</p>" + line(r"\angle " + q + p + r + r"=\angle " + p + q + "H")
    )


def trig_rows(model, wanted):
    t = model.triangle
    alpha = angle(model)
    name = trig(wanted, alpha)
    raw = t.function_latex
    value = t.sine if wanted == "sin" else t.cosine
    if t.function == wanted:
        return line(name + "=" + raw)
    if t.function in {"sin", "cos"}:
        given = trig(t.function, alpha)
        return (
            line(name + r"=\sqrt{1-(" + given + r")^2}")
            + line(name + r"=\sqrt{1-(" + raw + r")^2}")
            + line(name + "=" + number(value))
        )
    if wanted == "sin":
        beta = model.vertex + model.other_base_vertex + model.apex
        cot = trig("ctg", beta)
        tangent = trig("tg", alpha)
        cot_value = number(1 / t.function_value)
        return (
            line(
                cot + r"=\frac{1}{" + tangent + r"}=\frac{1}{" + raw + "}=" + cot_value
            )
            + line(name + r"=\sqrt{\frac{1}{1+(" + cot + r")^2}}")
            + line(
                name + r"=\sqrt{\frac{1}{1+(" + cot_value + r")^2}}=" + number(value)
            )
        )
    return line(name + r"=\sqrt{\frac{1}{1+(" + trig("tg", alpha) + r")^2}}") + line(
        name + r"=\sqrt{\frac{1}{1+(" + raw + r")^2}}=" + number(value)
    )


def _direct_base(model):
    wanted = "sin" if model.requested_kind == "height" else "cos"
    target = model.height_segment if wanted == "sin" else model.projection_segment
    base = model.base_segment
    value = model.triangle.sine if wanted == "sin" else model.triangle.cosine
    beta = model.vertex + model.other_base_vertex + "H"
    return (
        intro(model)
        + trig_rows(model, wanted)
        + line(
            target
            + "="
            + base
            + trig(wanted, beta)
            + "="
            + base
            + trig(wanted, angle(model))
        )
        + line(
            target
            + "=("
            + model.triangle.length_latex
            + r")\cdot("
            + number(value)
            + ")"
        )
        + line(target + "=" + exact_answer(model.answer).replace(",", "{,}"))
    )


def _side_body(model):
    t = model.triangle
    alpha = angle(model)
    base = model.base_segment
    side = model.side_segment
    half = model.vertex + "K"
    body = (
        intro(model)
        + f"<p>Высота {model.apex + 'K'}, проведенная из вершины {model.apex}, делит основание {base} пополам:</p>"
        + line(base + "=2" + half)
    )
    if model.requested_kind == "projection" and t.function == "sin":
        cosine = trig("cos", alpha)
        sine = trig("sin", alpha)
        body += line(
            model.projection_segment
            + "="
            + base
            + cosine
            + "=2"
            + half
            + cosine
            + "=2"
            + side
            + "("
            + cosine
            + ")^2"
        )
        body += line("(" + cosine + ")^2=1-(" + sine + ")^2")
        body += line(model.projection_segment + "=2" + side + "(1-(" + sine + ")^2)")
        body += line(
            model.projection_segment
            + r"=2\cdot("
            + t.length_latex
            + ")(1-("
            + t.function_latex
            + ")^2)"
        )
    else:
        wanted = "sin" if model.requested_kind == "height" else "cos"
        missing = "cos" if t.function == "sin" else wanted
        body += trig_rows(model, missing)
        target = model.height_segment if wanted == "sin" else model.projection_segment
        function = trig(wanted, alpha)
        body += line(
            target
            + "="
            + base
            + function
            + "=2"
            + half
            + function
            + "=2"
            + side
            + trig("cos", alpha)
            + function
        )
        value = t.sine if wanted == "sin" else t.cosine
        body += line(
            target
            + r"=2\cdot("
            + t.length_latex
            + r")\cdot("
            + number(t.cosine)
            + r")\cdot("
            + number(value)
            + ")"
        )
    body += line(model.requested + "=" + exact_answer(model.answer).replace(",", "{,}"))
    return body


def _inverse(model):
    base = model.base_segment
    height = model.height_segment
    projection = model.projection_segment
    b = model.triangle.length_latex
    h = model.given_height[1]
    name = trig(model.requested_kind, model.given_angle)
    body = intro(model)
    if model.requested_kind == "sin":
        body += line(
            name
            + "="
            + trig("sin", model.vertex + model.other_base_vertex + "H")
            + r"=\frac{"
            + height
            + "}{"
            + base
            + "}"
        )
        body += line(name + r"=\frac{" + h + "}{" + b + "}")
    else:
        body += f"<p>Найдем проекцию {projection} по теореме Пифагора:</p>"
        body += line(projection + r"=\sqrt{" + base + "^2-" + height + "^2}")
        body += line(
            projection
            + r"=\sqrt{("
            + b
            + ")^2-("
            + h
            + ")^2}="
            + number(model.projection)
        )
        body += line(
            name
            + "="
            + trig("cos", model.vertex + model.other_base_vertex + "H")
            + r"=\frac{"
            + projection
            + "}{"
            + base
            + "}"
        )
        body += line(name + r"=\frac{" + number(model.projection) + "}{" + b + "}")
    return body + line(name + "=" + exact_answer(model.answer).replace(",", "{,}"))


def _note(model):
    q, r = model.other_base_vertex, model.apex
    if model.topology > 0:
        text = f"Расстояние {q + 'H'} получилось больше длины {q + r}. Описанный треугольник тупоугольный, а основание высоты H лежит на продолжении стороны {q + r} за точку {r}. Это не влияет на корректность решения."
    elif model.topology < 0:
        text = f"Расстояние {q + 'H'} меньше длины {q + r}, поэтому основание высоты H лежит внутри стороны {q + r}. Треугольник остроугольный."
    else:
        text = f"Расстояние {q + 'H'} равно длине {q + r}: H совпадает с {r}, а треугольник прямоугольный."
    return "<p><b>Примечание</b>.</p><p>" + text + "</p>"


def render(model, rule):
    from .side_altitude_alternatives import cosine_projection, side_sine_height

    model.require_rule(rule)
    if model.given_kind == "base_height":
        body = _inverse(model)
    elif model.given_kind == "side":
        body = _side_body(model)
    else:
        body = _direct_base(model)
    if rule == "isosceles-triangle-27327-projection-from-side-sine":
        body += _note(model)
    html = solution_section("Решение", body)
    if rule == "isosceles-triangle-27323-projection-from-base-cosine":
        html += solution_section("Альтернативное решение.", cosine_projection(model))
    if rule == "isosceles-triangle-27326-altitude-from-side-sine":
        html += solution_section("Приведем другое решение", side_sine_height(model))
    return html
