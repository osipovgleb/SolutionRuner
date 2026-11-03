"""Keep each equal-side parent's angle method, with explicit numerical steps."""

import hashlib

from ...core.errors import ContentPlanError
from ...probability.common import line
from ..isosceles.angle_proofs import angle, degree
from ..right.altitude_methods import solution_section

PARENTS = {
    "general-triangle-27769-extension-isosceles-angle": "4ce83d90824297e088fe7a5716550f7b890f0dd7f6250a0c961cb66b1a384a8e",
    "general-triangle-27776-bisector-congruent-angle": "04317116ca7b2d2aef49735495a9d13868072772761de6ea75258a7f5141e3fe",
}


def review_parent(html, rule):
    if not isinstance(html, str) or hashlib.sha256(
        html.encode()
    ).hexdigest() != PARENTS.get(rule):
        raise ContentPlanError("the complete equal-side parent method must be reviewed")


def _extension(m):
    a, b, c, cbd, d = [angle(m.name(n)) for n in ["A", "B", "C", "CBD", "D"]]
    adjacent = 180 - m.beta
    return (
        f"<p>Сумма углов треугольника {m.name('ABC')} равна 180°, поэтому:</p>"
        + line(b + r"=180^{\circ}-" + a + "-" + c)
        + line(b + r"=180^{\circ}-" + degree(m.alpha) + "-" + degree(m.gamma))
        + line(b + "=" + degree(m.beta))
        + f"<p>Угол {m.name('CBD')} смежный с углом {m.name('B')}, поэтому:</p>"
        + line(cbd + r"=180^{\circ}-" + b)
        + line(cbd + r"=180^{\circ}-" + degree(m.beta))
        + line(cbd + "=" + degree(adjacent))
        + f"<p>Треугольник {m.name('CBD')} — равнобедренный, так как {m.name('BD')} = {m.name('BC')}. Углы при основании равны. Следовательно:</p>"
        + line(d + r"=\frac{180^{\circ}-" + cbd + "}{2}")
        + line(d + r"=\frac{180^{\circ}-" + degree(adjacent) + "}{2}")
        + line(d + "=" + degree(m.answer))
    )


def _congruent(m):
    b, c, dea, deb, bde = [angle(m.name(n)) for n in ["B", "C", "DEA", "DEB", "BDE"]]
    adjacent = 180 - m.gamma
    return (
        f"<p>Треугольники {m.name('CAD')} и {m.name('EAD')} равны по двум сторонам и углу между ними: {m.name('AD')} — общая сторона, {m.name('AE')} = {m.name('AC')}, а углы при {m.name('A')} равны, поскольку {m.name('AD')} — биссектриса. Поэтому:</p>"
        + line(c + "=" + dea + "=" + degree(m.gamma))
        + f"<p>Углы {m.name('DEA')} и {m.name('DEB')} смежные, поэтому:</p>"
        + line(deb + r"=180^{\circ}-" + dea)
        + line(deb + r"=180^{\circ}-" + degree(m.gamma))
        + line(deb + "=" + degree(adjacent))
        + f"<p>Сумма углов треугольника {m.name('BDE')} равна 180°. Следовательно:</p>"
        + line(bde + r"=180^{\circ}-" + b + "-" + deb)
        + line(bde + r"=180^{\circ}-" + degree(m.beta) + "-" + degree(adjacent))
        + line(bde + "=" + degree(m.answer))
    )


def render(model):
    return solution_section(
        "Решение", (_extension if model.mode == "extension" else _congruent)(model)
    )
