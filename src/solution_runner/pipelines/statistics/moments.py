"""Moments of binomial, two-point and independent random variables."""

import re
from fractions import Fraction

from .common import (
    CASED_COUNT,
    NUMBER,
    UnsupportedCondition,
    fmt,
    integer,
    line,
    number,
    plan,
    probability,
    result,
    sqrt_exact,
)
from .tables import solve as table_moments

_COIN = re.compile(
    r"Монету (?:подбрасывают|бросают) (?P<n>\d+) раз\. (?:Найдите математическое ожидание (?:количества|числа) выпавших орлов|Чему равно математическое ожидание числа выпавших орлов\?)\.?"
)
_DIE = re.compile(
    r"Кубик бросают (?P<n>\d+) раз\. Чему равно математическое ожидание числа выпавших единиц\?"
)
_BASKET = re.compile(
    rf"Баскетболист попадает в корзину с вероятностью (?P<p>{NUMBER})\. За игру он сделал (?P<n>\d+) бросков\. Чему равно математическое ожидание числа попаданий\?"
)
_BINOMIAL_PREFIX = rf"(?:Найти|Найдите) дисперсию дискретной случайной величины X — числа появлений события A в (?P<n>{CASED_COUNT}) независимых испытаниях, если "
_VARIANCE_P = re.compile(
    _BINOMIAL_PREFIX
    + rf"вероятность появления событий A в каждом испытании равна (?P<p>{NUMBER})\."
)
_VARIANCE_E = re.compile(
    _BINOMIAL_PREFIX
    + rf"вероятности появления события в этих испытаниях одинаковы и известно, что E\(X\)=(?P<e>{NUMBER})\."
)
_LINEAR = re.compile(
    rf"Случайные величины X и Y независимы\. Найти дисперсию случайной величины Z=(?P<a>-?\d+)X(?P<b>[+-]\d+)Y, если известно, что D\(X\)=(?P<dx>{NUMBER}), D\(Y\)=(?P<dy>{NUMBER})\."
)
_UNKNOWN_A = re.compile(
    rf"Случайная величина X принимает только два значения: 0 и a\(a\\gt ?0\)\. Найдите a, если известно, математическое ожидание E\(X\)=(?P<e>{NUMBER}) и дисперсия D\(X\)=(?P<d>{NUMBER})\."
)
_UNKNOWN_E = re.compile(
    rf"Случайная величина X принимает только два значения: 0 и a, где a\\gt ?0\. Известно, что P\(X=0\)=(?P<p>{NUMBER}), дисперсия D\(X\)=(?P<d>{NUMBER})\. Найдите математическое ожидание величины Х\."
)
_TWO_SCALED = re.compile(
    rf"Случайная величина X принимает два различных значения: a и (?P<c>\d+)a\. Известно, что P\(X=a\)=(?P<p>{NUMBER}), математическое ожидание E\(X\)=(?P<e>{NUMBER})\. Найдите среднеквадратичное отклонение\."
)
_BINOMIAL_SD = re.compile(
    rf"В серии из (?P<n>{CASED_COUNT}) независимых испытаний с постоянной вероятностью успеха p, где p\\gt ?\\frac\{{1\}}\{{2\}}, среднеквадратичное отклонение оказалось равным (?P<s>{NUMBER})\. Найдите математическое ожидание числа успехов\."
)
_COFFEE = re.compile(
    rf"В торговом центре два одинаковых автомата продают кофе\. Обслуживание автоматов происходит по вечерам после закрытия центра\. Вероятность события «К вечеру в первом автомате закончится кофе» равна (?P<a>{NUMBER})\. Вероятность события «К вечеру (?:во|в) втором автомате закончится кофе» равна (?P<b>{NUMBER})\. Считая эти события независимыми, найдите математическое ожидание числа автоматов, в которых к вечеру (?P<event>закончится|останется) кофе\."
)


def binomial(n, p, *, variance=False, combinatorial=False):
    probability(p)
    if n <= 0:
        raise UnsupportedCondition("the number of Bernoulli trials must be positive")
    html = "<p>Это независимые испытания с одной и той же вероятностью успеха. Обозначим число испытаний n, вероятность успеха p и вероятность неудачи q:</p>"
    html += line(rf"n={n},\quad p={fmt(p)},\quad q=1-p={fmt(1 - p)}")
    if combinatorial:
        html += "<p>Вероятность ровно k орлов даётся биномиальным распределением. Найдём ожидание по определению:</p>"
        html += line(rf"P(X=k)=C_{{{n}}}^k\left(\frac{{1}}{{2}}\right)^{{{n}}}")
        html += line(rf"E(X)=\frac{{1}}{{2^{{{n}}}}}\sum_{{k=0}}^{{{n}}}kC_{{{n}}}^k")
        html += "<p>Симметрия C(n,k)=C(n,n−k) позволяет попарно объединить слагаемые с k и n−k. В сумме их коэффициент равен n, поэтому:</p>"
        html += line(
            rf"2E(X)=\frac{{{n}}}{{2^{{{n}}}}}\sum_{{k=0}}^{{{n}}}C_{{{n}}}^k={n}"
        )
        html += line(rf"E(X)=\frac{{{n}}}{{2}}")
        html += (
            "<p>То же получается по формуле ожидания биномиального распределения:</p>"
        )
    if variance:
        html += "<p>Дисперсия биномиального распределения равна произведению числа испытаний и вероятностей успеха и неудачи:</p>"
        html += line(r"D(X)=np(1-p)") + line(
            rf"D(X)={n}\cdot {fmt(p)}\cdot {fmt(1 - p)}"
        )
        return result(n * p * (1 - p), html, "D(X)")
    html += line(r"E(X)=np") + line(rf"E(X)={n}\cdot {fmt(p)}")
    return result(n * p, html)


def _two_point(text):
    if match := _UNKNOWN_A.fullmatch(text):
        e, d = number(match["e"]), number(match["d"])
        if e <= 0 or d < 0:
            raise UnsupportedCondition(
                "the moments are inconsistent with nonnegative support"
            )
        a = (d + e * e) / e
        q = e / a
        probability(q, positive=True)
        html = "<p>Пусть q — вероятность значения a, тогда вероятность нуля равна 1−q. Найдём первый и второй моменты:</p>"
        html += line(r"E(X)=aq") + line(r"E(X^2)=a^2q") + line(r"D(X)=a^2q-(aq)^2")
        html += "<p>Из aq=E(X) выразим a через q и подставим в дисперсию. Сначала найдём вероятность q, затем значение a:</p>"
        html += line(rf"a=\frac{{{fmt(e)}}}{{q}}")
        html += line(rf"{fmt(d)}=\frac{{{fmt(e * e)}}}{{q}}-{fmt(e * e)}")
        html += line(rf"q=\frac{{{fmt(e * e)}}}{{{fmt(d + e * e)}}}={fmt(q)}")
        html += line(rf"a=\frac{{{fmt(e)}}}{{{fmt(q)}}}")
        return result(a, html, "a")
    if match := _UNKNOWN_E.fullmatch(text):
        p, d = number(match["p"]), number(match["d"])
        probability(p)
        if not 0 < p < 1 or d <= 0:
            raise UnsupportedCondition(
                "positive support requires a nondegenerate two-point law"
            )
        a = sqrt_exact(d / (p * (1 - p)))
        html = "<p>Пусть вероятность нуля равна p, а положительного значения a — q=1−p. Запишем моменты и дисперсию:</p>"
        html += (
            line(rf"p={fmt(p)},\quad q=1-p={fmt(1 - p)}")
            + line(r"E(X)=aq")
            + line(r"E(X^2)=a^2q")
            + line(r"D(X)=a^2q-a^2q^2=a^2pq")
        )
        html += line(
            rf"a^2=\frac{{{fmt(d)}}}{{{fmt(p)}\cdot {fmt(1 - p)}}}={fmt(a * a)}"
        ) + line(rf"a={fmt(a)},\quad a>0")
        return result(a * (1 - p), html + line(rf"E(X)={fmt(a)}\cdot {fmt(1 - p)}"))
    if match := _TWO_SCALED.fullmatch(text):
        c, p, e = int(match["c"]), number(match["p"]), number(match["e"])
        probability(p)
        if c == 1 or e == 0:
            raise UnsupportedCondition("the two support values must be distinct")
        a = e / (p + c * (1 - p))
        second = a * a * (p + c * c * (1 - p))
        d = second - e * e
        s = sqrt_exact(d)
        html = "<p>Вероятность второго значения равна 1−p. По математическому ожиданию найдём параметр a:</p>"
        html += line(rf"E(X)=a\cdot {fmt(p)}+{c}a\cdot {fmt(1 - p)}={fmt(e)}") + line(
            rf"a={fmt(a)}"
        )
        html += "<p>Вычислим второй момент, затем дисперсию и её квадратный корень:</p>"
        html += (
            line(
                rf"E(X^2)={fmt(a * a)}\cdot {fmt(p)}+{fmt(c * c * a * a)}\cdot {fmt(1 - p)}={fmt(second)}"
            )
            + line(rf"D(X)={fmt(second)}-{fmt(e * e)}={fmt(d)}")
            + line(rf"\sigma=\sqrt{{{fmt(d)}}}")
        )
        return result(s, html, r"\sigma")
    return None


def _coffee(match):
    a, b = number(match["a"]), number(match["b"])
    probability(a)
    probability(b)
    if match["event"] == "останется":
        a, b = 1 - a, 1 - b
    p2, p0 = a * b, (1 - a) * (1 - b)
    p1 = 1 - p0 - p2
    html = "<p>Пусть X — число автоматов с указанным в вопросе состоянием кофе. Возможны значения 0, 1 и 2. Найдём их вероятности по независимости:</p>"
    html += (
        line(rf"P(X=2)={fmt(a)}\cdot {fmt(b)}={fmt(p2)}")
        + line(rf"P(X=0)={fmt(1 - a)}\cdot {fmt(1 - b)}={fmt(p0)}")
        + line(rf"P(X=1)=1-{fmt(p2)}-{fmt(p0)}={fmt(p1)}")
    )
    html += (
        "<table><tbody><tr><td>Значения X</td><td>0</td><td>1</td><td>2</td></tr><tr><td>Вероятности</td>"
        + "".join(
            '<td><span data-inline-latex="' + fmt(p) + '"></span></td>'
            for p in (p0, p1, p2)
        )
        + "</tr></tbody></table>"
    )
    html += "<p>По определению математического ожидания:</p>" + line(
        rf"E(X)=0\cdot {fmt(p0)}+1\cdot {fmt(p1)}+2\cdot {fmt(p2)}"
    )
    html += (
        "<p>Вероятность ровно одного подходящего автомата можно проверить как сумму вероятностей несовместных случаев:</p>"
        + line(
            rf"P(X=1)={fmt(a)}\cdot {fmt(1 - b)}+{fmt(1 - a)}\cdot {fmt(b)}={fmt(p1)}"
        )
    )
    return result(p1 + 2 * p2, html)


def solve(text, tables):
    if tables:
        return table_moments(text, tables)
    if match := _COIN.fullmatch(text):
        return binomial(
            int(match["n"]),
            Fraction(1, 2),
            combinatorial=text.startswith("Монету подбрасывают"),
        )
    if match := _DIE.fullmatch(text):
        return binomial(int(match["n"]), Fraction(1, 6))
    if match := _BASKET.fullmatch(text):
        return binomial(int(match["n"]), number(match["p"]))
    if match := _VARIANCE_P.fullmatch(text):
        return binomial(integer(match["n"]), number(match["p"]), variance=True)
    if match := _VARIANCE_E.fullmatch(text):
        n, e = integer(match["n"]), number(match["e"])
        if n <= 0:
            raise UnsupportedCondition("positive trial count required")
        answer, html = binomial(n, e / n, variance=True)
        return (
            answer,
            "<p>Сначала выразим вероятность успеха из математического ожидания:</p>"
            + line(r"E(X)=np")
            + line(rf"p=\frac{{{fmt(e)}}}{{{n}}}={fmt(e / n)}")
            + html,
        )
    if match := _LINEAR.fullmatch(text):
        a, b, dx, dy = (
            int(match["a"]),
            int(match["b"]),
            number(match["dx"]),
            number(match["dy"]),
        )
        if dx < 0 or dy < 0:
            raise UnsupportedCondition("variance cannot be negative")
        html = (
            "<p>Для независимых величин дисперсии складываются. Постоянный множитель выносится из дисперсии в квадрате:</p>"
            + line(r"D(aX+bY)=a^2D(X)+b^2D(Y)")
            + line(rf"D(Z)=({a})^2\cdot {fmt(dx)}+({b})^2\cdot {fmt(dy)}")
        )
        return result(a * a * dx + b * b * dy, html, "D(Z)")
    if match := _BINOMIAL_SD.fullmatch(text):
        n, s = integer(match["n"]), number(match["s"])
        if n <= 0 or s < 0:
            raise UnsupportedCondition("invalid binomial moments")
        discriminant = 1 - 4 * s * s / n
        r = sqrt_exact(discriminant)
        p = (1 + r) / 2
        probability(p)
        if p <= Fraction(1, 2):
            raise UnsupportedCondition("no root satisfies p>1/2")
        html = (
            "<p>Возведём стандартное отклонение в квадрат и используем дисперсию биномиального распределения:</p>"
            + line(r"D(X)=np(1-p)")
            + line(rf"{n}p(1-p)={fmt(s * s)}")
            + line(rf"p^2-p+{fmt(s * s / n)}=0")
            + line(rf"p=\frac{{1\pm\sqrt{{{fmt(discriminant)}}}}}{{2}}")
        )
        html += (
            "<p>По условию p больше половины, поэтому выбираем больший корень:</p>"
            + line(rf"p={fmt(p)}")
            + line(rf"E(X)={n}\cdot {fmt(p)}")
        )
        return result(n * p, html)
    if match := _COFFEE.fullmatch(text):
        return _coffee(match)
    if found := _two_point(text):
        return found
    raise UnsupportedCondition("unsupported complete random-variable condition")


def build_context_repair_plan(context):
    return plan(context, solve)
