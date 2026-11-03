"""Preserve the parent exterior-angle and bisector methods with explicit arithmetic."""

import hashlib

from ...core.errors import ContentPlanError
from ...probability.common import line
from ..isosceles.angle_proofs import angle, degree
from ..right.altitude_methods import solution_section

PARENTS = {
    "general-triangle-681454-bisector-angle": "d440fb4dad8a051d18614a5634b2b5feb5537b9ec919c78fa07f7312c57eb43b",
    "general-triangle-27743-exterior-angle": "3717e31cd62af7cb4c70b1949d1113f506cc34ece49853809ceadf64ade68f5b",
    "general-triangle-27758-bisector-angle": "ad61a590100621c655219f35d8a849dc5bfcf8511c7de947dad5b20acd3380e4",
    "general-triangle-27759-bisector-exterior-angle": "6ab2f484633c5243931219a5be7efc3fc1b01b060bd543c2e404eb2078c468ae",
}


def review_parent(html, rule):
    if not isinstance(html, str) or hashlib.sha256(
        html.encode()
    ).hexdigest() != PARENTS.get(rule):
        raise ContentPlanError(
            "the complete simple-angle parent method must be reviewed"
        )


def _external(m):
    a, b, c = (angle(m.name(n)) for n in "ABC")
    external = b + r"_{\mathrm{внешн}}"
    return (
        "<p>Внешний угол треугольника равен сумме двух не смежных с ним внутренних углов:</p>"
        + line(external + "=" + degree(m.second))
        + line(external + "=" + a + "+" + c)
        + "<p>Вычтем известный внутренний угол и найдем искомый:</p>"
        + line(c + "=" + external + "-" + a)
        + line(c + "=" + degree(m.second) + "-" + degree(m.first))
        + line(c + "=" + degree(m.answer))
    )


def _base(m, named=False):
    a, b, c = (angle(m.name(n)) for n in (("CAB", "ABD", "ACB") if named else "ABC"))
    half = angle(m.name("BAD" if named else "CAD"))
    other_half = angle(m.name("CAD" if named else "BAD"))
    return (
        f"<p>Луч {m.name('AD')} — биссектриса, она делит угол {m.name('A')} пополам:</p>"
        + line(half + "=" + other_half + "=" + degree(m.second))
        + line(a + "=2" + half)
        + line(a + r"=2\cdot " + degree(m.second) + "=" + degree(2 * m.second))
        + "<p>Сумма углов треугольника равна 180°. Найдем третий угол:</p>"
        + line(b + r"=180^{\circ}-" + a + "-" + c)
        + line(b + r"=180^{\circ}-" + degree(2 * m.second) + "-" + degree(m.first))
        + ("" if named else line(b + r"=180^{\circ}-" + degree(2 * m.second + m.first)))
        + line(b + "=" + degree(m.angles[m.name("B")]))
    )


def _bisector_external(m):
    half, target, c = (angle(m.name(n)) for n in ("CAD", "ADB", "ACD"))
    return (
        f"<p>Луч {m.name('AD')} — биссектриса, поэтому половины угла равны:</p>"
        + line(half + "=" + angle(m.name("BAD")))
        + line(half + "=" + degree(m.second))
        + f"<p>Угол {m.name('ADB')} — внешний угол треугольника {m.name('ADC')}. Он равен сумме двух не смежных с ним углов:</p>"
        + line(target + "=" + half + "+" + c)
        + line(c + "=" + angle(m.name("C")) + "=" + degree(m.first))
        + line(target + "=" + degree(m.second) + "+" + degree(m.first))
        + line(target + "=" + degree(m.answer))
    )


def _named(m):
    body = _base(m, True)
    if m.mode == "bisector_base":
        return body
    target = angle(m.name("ADB"))
    return (
        body
        + f"<p>Теперь рассмотрим треугольник {m.name('ABD')} и найдем угол при основании биссектрисы по сумме его углов:</p>"
        + line(
            target
            + r"=180^{\circ}-"
            + angle(m.name("BAD"))
            + "-"
            + angle(m.name("ABD"))
        )
        + line(
            target
            + r"=180^{\circ}-"
            + degree(m.second)
            + "-"
            + degree(m.angles[m.name("B")])
        )
        + line(target + "=" + degree(m.answer))
    )


def render(m, rule=None):
    if rule == "general-triangle-681454-bisector-angle":
        return solution_section("Решение", _named(m))
    return solution_section(
        "Решение",
        {
            "external": _external,
            "bisector_base": _base,
            "bisector_external": _bisector_external,
        }[m.mode](m),
    )
