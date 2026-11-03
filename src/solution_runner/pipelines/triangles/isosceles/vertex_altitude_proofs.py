"""Preserve all included-angle/side-altitude parent methods and special triangles."""

import hashlib

from ...core.errors import ContentPlanError
from ...probability.common import line
from ..right.altitude_methods import solution_section
from .obtuse_proofs import _area_method
from .side_altitude_proofs import number, trig

_PARENTS = {
    "isosceles-triangle-27795-altitude-from-side-vertex-angle": "09e7e1de028d1241731634d462aa2d1cfbe70857b81dc3ab56a368544ab55bb3",
    "isosceles-triangle-27796-angle-from-side-altitude": "792c992d34c14d2c7a255fdd2fc25e5ccc2aabb77cff97b7d5110bdff41d7105",
    "isosceles-triangle-27797-side-from-altitude-vertex-angle": "ebaf32d4ed2541540ac93ff283525bf19f1178b5e38a912e3da0b994d67fb217",
    "isosceles-triangle-27798-obtuse-altitude-from-side-angle": "b932c9308a03441a8a38f33f353ea1b307f715b6ead40cd21045ad91b8d93eac",
}


def review_parent(html, rule):
    if not isinstance(html, str) or hashlib.sha256(
        html.encode()
    ).hexdigest() != _PARENTS.get(rule):
        raise ContentPlanError("all vertex-altitude parent methods must be reviewed")


def _angle_rows(m):
    if m.topology < 0:
        return m.apex, m.apex_angle, ""
    alpha = m.vertex + m.apex + "H"
    value = 180 - m.apex_angle
    body = f"<p>Основание высоты H лежит на продолжении стороны {m.other_side} за вершину {m.apex}. Смежные углы в сумме дают 180°:</p>"
    body += line(r"\angle " + alpha + r"=180^{\circ}-\angle " + m.apex)
    body += line(
        r"\angle "
        + alpha
        + r"=180^{\circ}-"
        + number(m.apex_angle)
        + r"^{\circ}="
        + number(value)
        + r"^{\circ}"
    )
    return alpha, value, body


def _coincident(m):
    body = f"<p>Угол при вершине {m.apex} прямой, поэтому стороны {m.side_segment} и {m.other_side} перпендикулярны. Высота {m.height_segment} совпадает со стороной {m.side_segment}, а H совпадает с {m.apex}:</p>"
    body += line(m.height_segment + "=" + m.side_segment + "=" + number(m.side))
    if m.mode == "height_angle" and m.requested != m.side_segment:
        body += line(m.requested + "=" + m.side_segment + "=" + number(m.side))
    return body


def _right_trig(m):
    body = f"<p>При прямом угле {m.apex} основание высоты H совпадает с {m.apex}. Используем значение синуса прямого угла:</p>"
    body += line(trig("sin", m.apex) + r"=\sin 90^{\circ}=1")
    if m.mode == "side_angle":
        body += line(m.height_segment + "=" + m.side_segment + trig("sin", m.apex))
        return body + line(
            m.height_segment + "=(" + m.side_raw + r")\cdot1=" + number(m.height)
        )
    body += line(
        m.side_segment
        + r"=\frac{"
        + m.height_segment
        + "}{"
        + trig("sin", m.apex)
        + "}"
    )
    body += line(m.side_segment + r"=\frac{" + m.height_raw + "}{1}=" + number(m.side))
    if m.requested != m.side_segment:
        body += line(m.requested + "=" + m.side_segment + "=" + number(m.side))
    return body


def _direct(m):
    if m.topology == 0:
        return _right_trig(m)
    alpha, value, body = _angle_rows(m)
    target = m.height_segment
    side = m.side_segment
    body += f"<p>В прямоугольном треугольнике {m.vertex + m.apex + 'H'} высота {target} — катет, противолежащий острому углу {alpha}:</p>"
    body += line(target + "=" + side + trig("sin", alpha))
    body += line(target + "=(" + m.side_raw + r")\sin " + number(value) + r"^{\circ}")
    body += line(r"\sin " + number(value) + r"^{\circ}=" + number(m.sine))
    body += line(target + "=(" + m.side_raw + r")\cdot(" + number(m.sine) + ")")
    return body + line(target + "=" + number(m.height))


def _inverse(m):
    if m.topology == 0:
        return _right_trig(m)
    alpha, value, body = _angle_rows(m)
    side = m.side_segment
    body += f"<p>Найдем длину стороны {side} из прямоугольного треугольника {m.vertex + m.apex + 'H'}:</p>"
    body += line(side + r"=\frac{" + m.height_segment + "}{" + trig("sin", alpha) + "}")
    body += line(
        side + r"=\frac{" + m.height_raw + r"}{\sin " + number(value) + r"^{\circ}}"
    )
    body += line(r"\sin " + number(value) + r"^{\circ}=" + number(m.sine))
    body += line(side + "=(" + m.height_raw + r")\cdot(" + number(1 / m.sine) + ")")
    body += line(side + "=" + number(m.side))
    if m.requested != side:
        body += "<p>Боковые стороны равны:</p>" + line(
            m.requested + "=" + side + "=" + number(m.side)
        )
    return body


def _geometric_height(m):
    if m.topology == 0:
        return _coincident(m)
    h, s = m.height_segment, m.side_segment
    projection = m.apex + "H"
    body = f"<p>Треугольник {m.vertex + m.apex + 'H'} прямоугольный, отрезок {s} — гипотенуза.</p>"
    if m.apex_angle == 30:
        body += f"<p>Катет {h} лежит напротив угла в 30°, поэтому вдвое меньше гипотенузы:</p>"
        return (
            body
            + line(h + r"=\frac{" + s + "}{2}")
            + line(h + r"=\frac{" + m.side_raw + "}{2}=" + number(m.height))
        )
    if m.apex_angle == 45:
        body += "<p>Его острые углы равны 45°, значит, катеты равны. По теореме Пифагора:</p>"
        body += line(h + "=" + projection) + line(s + "^2=2" + h + "^2")
        return body + line(
            h
            + r"=\frac{"
            + s
            + r"}{\sqrt{2}}=\frac{"
            + m.side_raw
            + r"}{\sqrt{2}}="
            + number(m.height)
        )
    body += "<p>Найдем второй катет по определению косинуса, затем искомый — по теореме Пифагора:</p>"
    body += line(
        projection + "=" + s + trig("cos", m.apex) + "=" + number(m.projection)
    )
    body += line(h + r"=\sqrt{" + s + "^2-" + projection + "^2}")
    return body + line(
        h
        + r"=\sqrt{("
        + m.side_raw
        + ")^2-("
        + number(m.projection)
        + ")^2}="
        + number(m.height)
    )


def _geometric_angle(m):
    h, s = m.height_segment, m.side_segment
    projection = m.apex + "H"
    gamma = r"\angle " + m.apex
    body = f"<p>В прямоугольном треугольнике {m.vertex + m.apex + 'H'} отрезок {s} — гипотенуза.</p>"
    if m.apex_angle == 30:
        body += line(h + r"=\frac{" + s + "}{2}") + line(
            m.side_segment + "=2" + m.height_segment + "=" + number(m.side)
        )
        return (
            body
            + "<p>Угол, лежащий против катета, равного половине гипотенузы, равен 30°:</p>"
            + line(gamma + r"=30^{\circ}")
        )
    body += "<p>По теореме Пифагора найдем другой катет:</p>"
    body += line(projection + r"=\sqrt{" + s + "^2-" + h + "^2}")
    body += line(
        projection
        + r"=\sqrt{("
        + m.side_raw
        + ")^2-("
        + m.height_raw
        + ")^2}="
        + number(m.projection)
    )
    if m.apex_angle == 45:
        body += line(h + "=" + projection)
        return (
            body
            + "<p>Катеты равны, поэтому острые углы прямоугольного треугольника равны:</p>"
            + line(gamma + r"=\frac{180^{\circ}-90^{\circ}}{2}=45^{\circ}")
        )
    if m.apex_angle == 60:
        body += line(projection + r"=\frac{" + s + "}{2}")
        body += "<p>Другой острый угол лежит против катета, равного половине гипотенузы:</p>"
        body += line(r"\angle " + m.apex + m.vertex + "H" + r"=30^{\circ}")
        return body + line(gamma + r"=90^{\circ}-30^{\circ}=60^{\circ}")
    body += "<p>По отношению противолежащего катета к гипотенузе определяем острый угол:</p>"
    return (
        body
        + line(trig("sin", m.apex) + r"=\frac{" + h + "}{" + s + "}=" + number(m.sine))
        + line(gamma + "=" + number(m.apex_angle) + r"^{\circ}")
    )


def _sine_angle(m):
    name = trig("sin", m.apex)
    return (
        f"<p>По определению синуса в прямоугольном треугольнике {m.vertex + m.apex + 'H'}:</p>"
        + line(name + r"=\frac{" + m.height_segment + "}{" + m.side_segment + "}")
        + line(
            name + r"=\frac{" + m.height_raw + "}{" + m.side_raw + "}=" + number(m.sine)
        )
        + "<p>Треугольник остроугольный. Найденному значению синуса соответствует острый угол:</p>"
        + line(name + r"=\sin " + number(m.apex_angle) + r"^{\circ}")
        + line(r"\angle " + m.apex + "=" + number(m.apex_angle) + r"^{\circ}")
    )


def render(m, rule):
    m.require_rule(rule)
    if m.mode == "side_height":
        return (
            solution_section("Решение", _geometric_angle(m))
            + solution_section("Приведем другое решение", _sine_angle(m))
            + solution_section(
                "Приведем еще одно решение",
                _area_method(m)
                + "<p>Искомый угол острый:</p>"
                + line(r"\angle " + m.apex + "=" + number(m.apex_angle) + r"^{\circ}"),
            )
        )
    if m.mode == "height_angle":
        return solution_section("Решение", _inverse(m))
    html = solution_section("Решение", _direct(m))
    if m.topology <= 0:
        html += solution_section("Альтернативное решение.", _geometric_height(m))
    return html
