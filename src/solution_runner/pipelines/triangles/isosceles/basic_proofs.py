"""Preserve the reviewed half-base proofs and their angular alternative."""

import hashlib

import sympy as sp

from ...core.errors import ContentPlanError
from ...probability.common import line
from ..right.altitude_methods import solution_section
from ..right.altitude_parent import exact_answer

_PARENTS = {
    "isosceles-triangle-27284-base-from-sine": "0b33c97ad94f991000f2bc53f9bf31a0aa9bebc69033c89cd4847b9bf87e099f",
    "isosceles-triangle-27285-side-from-base-sine": "0c0ca5c8cf007514d4859f0eef828f384f3cd693c3770296780c352643bea4f2",
    "isosceles-triangle-27286-base-from-cosine": "cc3d03840d4bd9fb58d7064fb16618dadf656b461a0a0c5947c0761350d0cfeb",
    "isosceles-triangle-27287-side-from-base-cosine": "dd153029688ba7a4224e84bacab0fbaa6ef9a8cd1491920dfbdf434c7c8d21d8",
    "isosceles-triangle-27288-base-from-tangent": "63b9c785eb12ddde3756c4c75941b9d5c2aaae9dacb967f613b3233efe4239c8",
    "isosceles-triangle-27289-side-from-base-tangent": "d3805461a125ca55837fca862de9b881b6516871ce495c49f745e13de2cbbec8",
}


def review_parent(html, rule):
    if not isinstance(html, str) or hashlib.sha256(
        html.encode()
    ).hexdigest() != _PARENTS.get(rule):
        raise ContentPlanError("the complete isosceles parent methods must be reviewed")


def _latex(value):
    return sp.latex(sp.simplify(value)).replace(r" \sqrt", r"\sqrt")


def _cosine(model):
    name = r"\cos " + model.angle
    raw = model.function_latex
    if model.function == "cos":
        return line(name + "=" + raw)
    if model.function == "sin":
        formula = r"\sqrt{1-\sin^{2} " + model.angle + "}"
        substitution = r"\sqrt{1-(" + raw + ")^{2}}"
    else:
        formula = r"\sqrt{\frac{1}{1+\tg^{2} " + model.angle + "}}"
        substitution = r"\sqrt{\frac{1}{1+(" + raw + ")^{2}}}"
    return (
        line(name + "=" + formula)
        + line(name + "=" + substitution)
        + line(name + "=" + _latex(model.cosine))
    )


def _primary(model):
    angle = model.angle
    leg, projection = ("AC", "AH") if angle == "A" else ("BC", "BH")
    cosine = r"\cos " + angle
    answer = exact_answer(model.answer).replace(",", "{,}")
    body = (
        "<p>Треугольник ABC — равнобедренный, поэтому высота CH делит основание AB пополам:</p>"
        + line(r"AH=BH=\frac{AB}{2}")
    )
    body += (
        "<p>Углы A и B равны и являются острыми. Найдем положительное значение косинуса нужного угла:</p>"
        + _cosine(model)
    )
    if model.given_kind == "side":
        body += "<p>Следовательно:</p>" + line(
            "AB=2" + projection + "=2" + leg + cosine
        )
        body += line(
            "AB=2\\cdot(" + model.length_latex + r")\cdot(" + _latex(model.cosine) + ")"
        )
        body += line("AB=" + answer)
    else:
        body += "<p>Тогда:</p>" + line(
            leg
            + r"=\frac{"
            + projection
            + "}{"
            + cosine
            + r"}=\frac{AB}{2"
            + cosine
            + "}"
        )
        body += line(
            leg
            + r"=\frac{"
            + model.length_latex
            + "}{2\\cdot("
            + _latex(model.cosine)
            + ")}"
        )
        body += line(
            model.requested
            + ("=" + leg if model.requested != leg else "")
            + "="
            + answer
        )
    return body


def _alternative(model):
    angle = model.angle
    answer = exact_answer(model.answer).replace(",", "{,}")
    if model.cosine == sp.Rational(1, 2):
        return (
            "<p>Косинус данного угла равен 0,5, значит:</p>"
            + line(r"\angle " + angle + r"=60^{\circ}")
            + "<p>Равнобедренный треугольник с углом 60° является равносторонним. Следовательно, все его стороны равны:</p>"
            + line("AB=AC=BC=" + answer)
        )
    leg, opposite = ("AC", "B") if angle == "A" else ("BC", "A")
    body = "<p>Углы A и B равны. Выразим отношение основания к боковой стороне через косинус данного угла:</p>"
    body += line(r"\angle C=180^{\circ}-2\angle " + angle)
    body += line(r"\sin C=\sin(2" + angle + r")=2\sin " + angle + r"\cos " + angle)
    body += "<p>По теореме синусов и равенству углов при основании:</p>"
    body += line(
        r"\frac{AB}{"
        + leg
        + r"}=\frac{\sin C}{\sin "
        + opposite
        + r"}=\frac{2\sin "
        + angle
        + r"\cos "
        + angle
        + r"}{\sin "
        + angle
        + r"}=2\cos "
        + angle
    )
    if model.given_kind == "side":
        body += line(
            r"AB=2"
            + leg
            + r"\cos "
            + angle
            + r"=2\cdot("
            + model.length_latex
            + r")\cdot("
            + _latex(model.cosine)
            + ")="
            + answer
        )
    else:
        body += line(
            model.requested
            + ("=" + leg if model.requested != leg else "")
            + r"=\frac{AB}{2\cos "
            + angle
            + r"}=\frac{"
            + model.length_latex
            + r"}{2\cdot("
            + _latex(model.cosine)
            + ") }="
            + answer
        )
    return body


def render(model, *, figure_html=""):
    html = solution_section("Решение", figure_html + _primary(model))
    if model.function == "cos":
        title = (
            "Альтернативное решение."
            if model.given_kind == "side"
            else "Приведем другое решение"
        )
        html += solution_section(title, _alternative(model))
    return html
