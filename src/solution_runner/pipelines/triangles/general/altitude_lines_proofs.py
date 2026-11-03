"""Preserve both parent methods with the actual convexity and height-line rays."""

from ...probability.common import line
from ..isosceles.angle_proofs import angle, degree
from ..right.altitude_methods import solution_section


def _given(m):
    return f'Обозначим вершины так, что <span data-inline-latex="{angle("A")}={degree(m.alpha)}"></span> и <span data-inline-latex="{angle("B")}={degree(m.beta)}"></span>. Высоты AD и BE пересекаются в O, C — третья вершина. '


def _third(m):
    return line(
        angle("C") + r"=180^{\circ}-" + degree(m.alpha) + "-" + degree(m.beta)
    ) + line(angle("C") + "=" + degree(m.gamma))


def _convex(m):
    doe = 180 - m.gamma
    result = (
        "<p>Углы при основаниях высот прямые. Сумма углов в выпуклом четырёхугольнике DOEC равна 360°, следовательно:</p>"
        + line(angle("CDO") + "=" + angle("CEO") + r"=90^{\circ}")
        + line(
            angle("DOE")
            + r"=360^{\circ}-"
            + angle("CDO")
            + "-"
            + angle("CEO")
            + "-"
            + angle("C")
        )
        + line(angle("DOE") + r"=360^{\circ}-90^{\circ}-90^{\circ}-" + degree(m.gamma))
        + line(angle("DOE") + r"=180^{\circ}-" + degree(m.gamma))
        + line(angle("DOE") + "=" + degree(doe))
    )
    if m.gamma > 90:
        result += (
            "<p>Полученный угол острый. Искомый тупой угол θ между теми же прямыми смежный с ним:</p>"
            + line(r"\theta=180^{\circ}-" + angle("DOE"))
            + line(r"\theta=180^{\circ}-" + degree(doe) + "=" + degree(m.answer))
        )
    else:
        result += "<p>Угол DOE тупой, поэтому именно он является искомым.</p>"
    return result


def _crossed(m):
    p, own, other = ("A", "D", "E") if m.alpha > 90 else ("B", "E", "D")
    inner, opposite = "C" + p + own, other + p + "O"
    right1, right2 = p + own + "C", p + other + "O"
    at_o = p + "O" + other
    complement = 90 - m.gamma
    coincident = "OD и OA" if p == "A" else "OE и OB"
    return (
        f"<p>Угол {p} тупой, а четырёхугольник DOEC самопересекается. Формула суммы углов выпуклого четырёхугольника здесь неприменима. Рассмотрим вместо него прямоугольные треугольники {p}C{own} и {p}{other}O:</p>"
        + line(angle(right1) + "=" + angle(right2) + r"=90^{\circ}")
        + line(angle(inner) + r"=90^{\circ}-" + angle("C"))
        + line(
            angle(inner) + r"=90^{\circ}-" + degree(m.gamma) + "=" + degree(complement)
        )
        + f"<p>Оба луча угла {opposite} противоположны соответствующим лучам угла {inner}, поэтому эти углы равны. Найдём оставшийся угол прямоугольного треугольника:</p>"
        + line(angle(opposite) + "=" + angle(inner))
        + line(angle(at_o) + r"=180^{\circ}-" + angle(opposite) + "-" + angle(right2))
        + line(
            angle(at_o) + r"=90^{\circ}-" + degree(complement) + "=" + degree(m.gamma)
        )
        + f"<p>Лучи {coincident} совпадают, поэтому угол DOE равен найденному острому углу. Искомый тупой угол θ смежный с ним:</p>"
        + line(r"\theta=180^{\circ}-" + degree(m.gamma) + "=" + degree(m.answer))
    )


def _right(m):
    p, q, own = ("A", "B", "D") if m.alpha == 90 else ("B", "A", "E")
    inner, acute = "C" + p + own, own + p + q
    complement = 90 - m.gamma
    return (
        f"<p>Угол {p} прямой; одна из высот совпадает с прямой AB. Используем прямоугольный треугольник {p}C{own}, затем найдём острый угол между второй высотой и прямой AB:</p>"
        + line(angle(p + own + "C") + r"=90^{\circ}")
        + line(angle(inner) + r"=90^{\circ}-" + angle("C"))
        + line(
            angle(inner) + r"=90^{\circ}-" + degree(m.gamma) + "=" + degree(complement)
        )
        + line(angle(acute) + r"=90^{\circ}-" + angle(inner))
        + line(
            angle(acute) + r"=90^{\circ}-" + degree(complement) + "=" + degree(m.gamma)
        )
        + "<p>Искомый тупой угол θ смежный с полученным острым углом:</p>"
        + line(r"\theta=180^{\circ}-" + angle(acute))
        + line(r"\theta=180^{\circ}-" + degree(m.gamma) + "=" + degree(m.answer))
    )


def _second(m):
    total = m.alpha + m.beta
    selected = r"\varphi" if total > 90 else angle("C")
    return (
        "<p>Один из углов между высотами треугольника, проведёнными из двух его вершин, равен углу при третьей вершине: стороны этих углов соответственно перпендикулярны. "
        + _given(m)
        + "Найдём третий угол:</p>"
        + _third(m)
        + "<p>Другой угол, который обозначим через φ, равен сумме углов треугольника, из вершин которых проведены высоты:</p>"
        + line(r"\varphi=" + angle("A") + "+" + angle("B"))
        + line(r"\varphi=" + degree(m.alpha) + "+" + degree(m.beta))
        + line(r"\varphi=" + degree(total))
        + "<p>Выбираем из двух найденных углов тупой и обозначим его через θ:</p>"
        + line(r"\theta=" + selected + "=" + degree(m.answer))
    )


def render(m):
    if m.alpha == 90 or m.beta == 90:
        method = _right
    elif m.alpha > 90 or m.beta > 90:
        method = _crossed
    else:
        method = _convex
    first = (
        "<p>"
        + _given(m)
        + "Из суммы углов треугольника найдём угол C:</p>"
        + _third(m)
        + method(m)
    )
    return solution_section("Решение", first) + solution_section(
        "Приведём другое решение", _second(m)
    )
