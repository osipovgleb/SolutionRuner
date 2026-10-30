"""Survey intervals; exact radicals when the condition does not request rounding."""

import re
from fractions import Fraction

import sympy as sp

from .common import COUNT, UnsupportedCondition, count, fmt, line

_CLIENT = r"При выборочном обследовании клиентов сети автозаправочных станций «Огонек», (?P<k1>\d+) из (?P<n1>\d+) случайных респондентов ответили «Да» на вопрос, есть ли у них бонусная карта сети\. Найдите интервальную оценку доли клиентов, имеющих бонусную карту, "
_CITY = rf"При выборочном обследовании жителей города [А-Я]\. (?P<k2>{COUNT}) из (?P<n2>\d+) респондентов ответили «(?P<response>Да|Нет)» на вопрос, (?P<question>посещали ли они городской парк за последние полгода|понравился ли им новый торговый центр)\. Найдите интервальную оценку доли горожан, (?P<population>посещавших городской парк за полгода|не посещавших городской парк за полгода|которым торговый центр не понравился|которым торговый центр понравился), "
_PATTERN = re.compile(
    "(?:"
    + _CLIENT
    + "|"
    + _CITY
    + r")пользуясь правилом «частота плюс-минус (?P<c>\d+|одно) стандартн(?:ых отклонения|ое отклонение)»\. В ответ запишите (?P<side>верхнюю границу|нижнюю границу|длину) доверительного интервала\.(?: Ответ округлите до (?P<places>десятых|сотых|тысячных)\.)?"
)


def solve(text):
    match = _PATTERN.fullmatch(text)
    if match is None:
        return None
    k = count(match["k1"] or match["k2"])
    n = int(match["n1"] or match["n2"])
    c = count(match["c"])
    if n <= 0 or not 0 <= k <= n or c <= 0:
        raise UnsupportedCondition("invalid survey size or confidence multiplier")
    if match["k2"]:
        expected = {
            (
                "посещали ли они городской парк за последние полгода",
                "Да",
            ): "посещавших городской парк за полгода",
            (
                "посещали ли они городской парк за последние полгода",
                "Нет",
            ): "не посещавших городской парк за полгода",
            (
                "понравился ли им новый торговый центр",
                "Нет",
            ): "которым торговый центр не понравился",
            (
                "понравился ли им новый торговый центр",
                "Да",
            ): "которым торговый центр понравился",
        }
        if match["population"] != expected[(match["question"], match["response"])]:
            raise UnsupportedCondition(
                "the counted response does not describe the requested population share"
            )
    w = Fraction(k, n)
    variance = w * (1 - w) / n
    standard = sp.sqrt(sp.Rational(variance.numerator, variance.denominator))
    frequency = sp.Rational(k, n)
    value = (
        2 * c * standard
        if match["side"] == "длину"
        else frequency
        + (1 if match["side"] == "верхнюю границу" else -1) * c * standard
    )
    exact = sp.latex(sp.simplify(value))
    html = (
        "<p>Число нужных ответов имеет биномиальную дисперсию np(1−p). Для доли X/n стандартная ошибка равна:</p>"
        + line(r"\sigma_{X/n}=\frac{\sqrt{np(1-p)}}{n}=\sqrt{\frac{p(1-p)}{n}}")
    )
    html += (
        "<p>Истинная доля неизвестна. Оценим её относительной частотой указанных в условии ответов:</p>"
        + line(rf"n={n},\quad \omega=\frac{{{k}}}{{{n}}}={fmt(w)}")
    )
    html += line(r"\sigma_{\mathrm{выб}}=\sqrt{\frac{\omega(1-\omega)}{n}}") + line(
        r"\sigma_{\mathrm{выб}}=\sqrt{" + fmt(variance) + "}"
    )
    html += line(
        rf"\omega-{c}\sigma_{{\mathrm{{выб}}}}<p<\omega+{c}\sigma_{{\mathrm{{выб}}}}"
    )
    if match["side"] == "длину":
        html += "<p>Длина интервала равна разности его границ:</p>" + line(
            rf"L=(\omega+{c}\sigma_{{\mathrm{{выб}}}})-(\omega-{c}\sigma_{{\mathrm{{выб}}}})={2 * c}\sigma_{{\mathrm{{выб}}}}"
        )
    else:
        sign = "+" if match["side"] == "верхнюю границу" else "-"
        html += "<p>Возьмём указанную в вопросе границу:</p>" + line(
            rf"B=\omega{sign}{c}\sigma_{{\mathrm{{выб}}}}"
        )
    symbol = "L" if match["side"] == "длину" else "B"
    html += line(symbol + "=" + exact)
    if match["places"]:
        places = {"десятых": 1, "сотых": 2, "тысячных": 3}[match["places"]]
        # Bound the algebraic result at rational midpoints rather than rounding a float.
        scale = 10**places
        units = int(sp.floor(abs(value) * scale + sp.Rational(1, 2)))
        digits = str(units).zfill(places + 1)
        answer = ("-" if value < 0 else "") + digits[:-places] + "," + digits[-places:]
        html += "<p>Округлим до указанного в условии разряда:</p>" + line(
            symbol + r"\approx " + answer.replace(",", "{,}")
        )
    else:
        answer = exact
        html += (
            "<p>Точность округления не задана, поэтому сохраняем точное значение.</p>"
        )
    return answer, html
