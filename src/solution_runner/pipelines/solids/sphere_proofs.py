"""Keep the parents' surface, radius-ratio and sum-of-volumes methods."""

import sympy as sp

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value

SURFACE = r"4\pi"
VOLUME = r"\frac{4}{3}\pi"


def _ratio(symbol, large, small):
    return (
        r"\frac{" + symbol + "_" + str(large) + "}{" + symbol + "_" + str(small) + "}"
    )


def _great_circle(m):
    area = m.given[0]
    return (
        "<p>Площадь большого круга шара радиуса R равна:</p>"
        + line(r"S_0=\pi R^2")
        + line("S_0=" + value(area))
        + "<p>Площадь поверхности шара равна четырём площадям его большого круга:</p>"
        + line(r"S=4\pi R^2")
        + line("S=4S_0")
        + line(r"S=4\cdot" + bracket(area) + "=" + value(m.answer))
    )


def _surface_factor(m):
    large, small = m.large, m.small
    rratio = _ratio("R", large, small)
    sratio = _ratio("S", large, small)
    factor = m.given[0]
    k = m.radius_ratio
    intro = "<p>Площадь поверхности шара выражается через его радиус формулой:</p>"
    result = (
        intro
        + line("S_" + str(large) + "=" + SURFACE + " R_" + str(large) + "^2")
        + line("S_" + str(small) + "=" + SURFACE + " R_" + str(small) + "^2")
    )
    if m.input_kind == "volume":
        result += "<p>Найдём отношение объёмов шаров и извлечём кубический корень, чтобы получить отношение радиусов:</p>"
        result += line(_ratio("V", large, small) + "=" + rratio + "^3=" + value(factor))
        result += line(rratio + r"=\sqrt[3]{" + value(factor) + "}=" + value(k))
    elif m.input_kind == "diameter":
        result += "<p>Диаметр равен удвоенному радиусу, поэтому отношение радиусов равно отношению диаметров:</p>"
        result += line(rratio + "=" + _ratio("d", large, small) + "=" + value(factor))
    else:
        result += (
            "<p>По условию отношение большего радиуса к меньшему равно:</p>"
            + line(rratio + "=" + value(factor))
        )
    return (
        result
        + "<p>Площади поверхностей соотносятся как квадраты радиусов:</p>"
        + line(sratio + "=" + rratio + "^2")
        + line(sratio + "=" + bracket(k) + "^2=" + value(m.answer))
    )


def _volume_factor(m):
    factor = m.given[0]
    return (
        "<p>Объём шара радиуса R выражается формулой объёма шара. Обозначим исходный радиус через R₁, увеличенный — через R₂:</p>"
        + line("V_1=" + VOLUME + " R_1^3")
        + line("V_2=" + VOLUME + " R_2^3")
        + line("R_2=" + bracket(factor) + r"\cdot R_1")
        + "<p>Поэтому при увеличении радиуса объём увеличивается в куб отношения радиусов:</p>"
        + line(_ratio("V", 2, 1) + "=" + _ratio("R", 2, 1) + "^3")
        + line(_ratio("V", 2, 1) + "=" + bracket(factor) + "^3=" + value(m.answer))
    )


def _powers(parts, degree):
    return "+".join(p + "^" + str(degree) for p in parts)


def _numeric_sum(m, target, total):
    power = m.degree
    result = ""
    common = (
        sp.gcd_list(m.given)
        if power == 3 and all(r.is_Integer for r in m.given)
        else sp.Integer(1)
    )
    if common > 1:
        result += line(
            target
            + "^3="
            + bracket(common)
            + r"^3\left("
            + _powers([bracket(r / common) for r in m.given], power)
            + r"\right)"
        )
        result += line(
            target
            + "^3="
            + bracket(common)
            + r"^3\cdot"
            + bracket(total / common**3)
            + "="
            + value(total)
        )
    else:
        result += line(
            target
            + "^"
            + str(power)
            + "="
            + "+".join(value(r**power) for r in m.given)
            + "="
            + value(total)
        )
    return result


def _combined_radius(m):
    power = m.degree
    size = len(m.given)
    symbol = "S" if power == 2 else "V"
    coefficient = SURFACE if power == 2 else VOLUME
    target = "R_" + str(size + 1)
    names = ["R_" + str(i + 1) for i in range(size)]
    total = sp.simplify(sum(r**power for r in m.given))
    result = (
        "<p>Из условия равенства площадей поверхностей получаем:</p>"
        if power == 2
        else "<p>Объём шара вычисляется по формуле:</p>"
        + line("V=" + VOLUME + " R^3")
        + "<p>Поэтому из равенства объёма нового шара сумме данных объёмов получаем:</p>"
    )
    result += line(
        symbol
        + "_"
        + str(size + 1)
        + "="
        + "+".join(symbol + "_" + str(i + 1) for i in range(size))
    )
    result += line(
        coefficient
        + " "
        + target
        + "^"
        + str(power)
        + "="
        + "+".join(coefficient + " " + n + "^" + str(power) for n in names)
    )
    result += line(target + "^" + str(power) + "=" + _powers(names, power))
    result += "<p>Сократим общий множитель и подставим данные радиусы:</p>" + line(
        target + "^" + str(power) + "=" + _powers([bracket(r) for r in m.given], power)
    )
    result += _numeric_sum(m, target, total)
    root = r"\sqrt{" if power == 2 else r"\sqrt[3]{"
    return (
        result
        + "<p>Радиус положителен. Извлечём соответствующий корень:</p>"
        + line(target + "=" + root + value(total) + "}=" + value(m.answer))
    )


def _surface_over_pi(m):
    amount = m.given[0]
    cube = sp.simplify(3 * amount / 4)
    radius = cube ** sp.Rational(1, 3)
    return (
        "<p>Объём шара радиуса R вычисляется по формуле:</p>"
        + line("V=" + VOLUME + " R^3")
        + line(r"R^3=\frac{3V}{4\pi}")
        + "<p>Подставим данный объём и найдём радиус:</p>"
        + line(r"R^3=\frac{3\cdot" + bracket(amount) + r"\pi}{4\pi}=" + value(cube))
        + line(r"R=\sqrt[3]{" + value(cube) + "}=" + value(radius))
        + "<p>Теперь найдём площадь поверхности:</p>"
        + line("S=" + SURFACE + " R^2")
        + line(
            "S="
            + SURFACE
            + r"\cdot"
            + bracket(radius)
            + "^2="
            + bracket(m.answer)
            + r"\pi"
        )
        + "<p>По условию требуется площадь поверхности, делённая на π:</p>"
        + line(
            r"\frac{S}{\pi}=\frac{"
            + bracket(m.answer)
            + r"\pi}{\pi}="
            + value(m.answer)
        )
    )


def render(m):
    return {
        "great_circle_surface": _great_circle,
        "surface_factor": _surface_factor,
        "volume_factor": _volume_factor,
        "combined_radius": _combined_radius,
        "surface_over_pi": _surface_over_pi,
    }[m.mode](m)
