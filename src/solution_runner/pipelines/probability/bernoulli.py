"""Exact independent-trial events, fixed orders and binomial probability ratios."""

import re
from dataclasses import dataclass
from fractions import Fraction
from math import comb

from solution_runner.pipelines.core.numbers import (
    format_answer,
    parse_rational,
)
from solution_runner.pipelines.core.numbers import format_latex_fraction as fmt

from .common import (
    COUNT,
    NUMBER,
    UnsupportedCondition,
    count,
    finish,
    line,
    normalize,
    require_content,
    rounded,
    rounding,
)

RATIONAL = rf"(?:{NUMBER}|\\frac\{{\d+\}}\{{[1-9]\d*\}})"
CASED = rf"(?:{COUNT}|пяти|четырех|трех|двух)"
_CASES = {"пяти": 5, "четырех": 4, "трех": 3, "двух": 2}


def cardinal(word):
    return _CASES[word] if word in _CASES else count(word)


def checked(p):
    if not 0 <= p <= 1:
        raise UnsupportedCondition("a trial probability must lie between zero and one")
    return p


def result(value, html, places=None, symbol="P"):
    answer = format_answer(value) if places is None else rounded(value, places)
    relation = "=" if Fraction(answer.replace(",", ".")) == value else r"\approx "
    return answer, html + line(symbol + relation + answer.replace(",", "{,}"))


@dataclass(frozen=True)
class Trial:
    n: int
    p: Fraction
    kind: str
    k: int = 0
    other: int = 0
    style: str = ""
    places: int | None = None
    shot_p: Fraction | None = None


_PHONE = re.compile(
    r"Какова вероятность того, что (?:случайно выбранный телефонный номер оканчивается двумя четными цифрами|в случайно выбранном телефонном номере последняя цифра четная, а предпоследняя — нечетная)\?"
)
_VOLLEY = re.compile(
    r"Перед началом волейбольного матча капитаны команд тянут (?:честный )?жребий, чтобы определить, какая из команд начнет игру с мячом\. Команда «(?P<team>[^«»]+)» по очереди играет с командами «(?P<a>[^«»]+)», «(?P<b>[^«»]+)» и «(?P<c>[^«»]+)»\. Найдите вероятность того, что «(?P=team)» будет начинать (?:с мячом )?только (?P<games>первую и последнюю игры|вторую и последнюю игры|вторую игру)\."
)
_BATTERIES = re.compile(
    rf"Вероятность того, что батарейка бракованная, равна (?P<p>{NUMBER})\. Покупатель в магазине выбирает случайную упаковку, в которой (?P<n>{COUNT}) таких батарейки\. Найдите вероятность того, что обе батарейки окажутся исправными\."
)
_SELLERS = re.compile(
    rf"В магазине (?P<n>{COUNT}) продавца\. Каждый из них занят (?P<description>с клиентом|обслуживанием клиента) с вероятностью (?P<p>{NUMBER})(?P<independent> независимо от других продавцов)?\. Найдите вероятность того, что в случайный момент времени все (?P<all>{COUNT}) продавца заняты(?P<ending> одновременно \(считайте, что клиенты заходят независимо друг от друга\))?\."
)
_LAMPS = re.compile(
    rf"Помещение освещается фонарем с (?P<n>двумя|тремя) лампами\. Вероятность перегорания (?:одной )?лампы в течение года равна (?P<p>{NUMBER})\. Найдите вероятность того, что в течение года хотя бы одна лампа не перегорит\."
)
_TERMINALS = re.compile(
    rf"В магазине стоят два платежных автомата\. Каждый из них может быть неисправен с вероятностью (?P<p>{NUMBER}) независимо от другого автомата\. Найдите вероятность того, что хотя бы один автомат исправен\."
)
_TERMINAL_DAY = re.compile(
    rf"Платежный терминал в течение рабочего дня может выйти из строя\. Вероятность этого события (?P<p>{NUMBER})\. В торговом центре независимо друг от друга работают два таких платежных терминала\. Найдите вероятность того, что хотя бы один из них в течение рабочего дня будет исправен\."
)
_BIATHLON = re.compile(
    rf"Биатлонист (?P<n>{COUNT}) раз(?:а)? стреляет по мишеням\. Вероятность попадания в мишень при одном выстреле равна (?P<p>{NUMBER})\. Найдите вероятность того, что биатлонист первые (?P<k>{COUNT}) раза попал в мишени, а (?P<last>последние (?P<m>{COUNT}) промахнулся|последний раз промахнулся)\."
)
_TARGETS = re.compile(
    rf"Стрелок стреляет по одному разу в каждую из (?P<n>{CASED}) мишеней\. Вероятность попадания в мишень при каждом отдельном выстреле равна (?P<p>{NUMBER})\. Найдите вероятность того, что стрелок попадет в (?P<first>первую мишень|(?P<k>{COUNT}) первые мишени) и не попадет в (?P<m>{COUNT}) последни(?:е|х)\."
)
_TARGETS_SHORT = re.compile(
    rf"Стрелок стреляет по (?P<n>\d+) одинаковым мишеням по одному разу, вероятность промаха (?P<p>{NUMBER}), найдите вероятность что он попадет в первую мишень, а в (?P<m>\d+) оставшиеся промахнется\."
)
_LIGHT = re.compile(
    rf"Линия подсветки состоит из 4 ламп\. Каждая лампа работает независимо от других, и вероятность ее перегорания в течение года равна (?P<p>{NUMBER})\. Найдите вероятность того, что в течение года первая и третья лампы перегорят, а вторая и четвертая не перегорят\."
)
_HIT = re.compile(
    rf"Стрелок стреляет по мишени один раз\. В случае промаха стрелок делает второй выстрел по той же мишени\. Вероятность попасть в мишень при одном выстреле равна (?P<p>{NUMBER})\. Найдите вероятность того, что мишень будет поражена \(либо первым, либо вторым выстрелом\)\."
)
_HIT_LIMIT = re.compile(
    rf"Стрелок при каждом выстреле поражает мишень с вероятностью (?P<p>{NUMBER}), независимо от результатов предыдущих выстрелов\. Какова вероятность того, что он поразит мишень, сделав не более (?P<n>\d+) выстрелов\?"
)
_SMS = re.compile(
    rf"Телефон передает SMS-сообщение\. В случае неудачи телефон делает следующую попытку\. Вероятность того, что сообщение удастся передать без ошибок в каждой отдельной попытке, равна (?P<p>{NUMBER})\. Найдите вероятность того, что для передачи сообщения потребуется не больше (?P<n>{CASED}) попыток\."
)
_RATIO_COIN = re.compile(
    rf"Симметричную монету бросают (?P<n>\d+) раз\. Во сколько раз вероятность события «выпа(?:дет|ло) ровно (?P<k>{COUNT}) орл(?:а|ов)» (?P<direction>больше|меньше) вероятности события «выпадет ровно (?P<other>{COUNT})[ ~]орл(?:а|ов)»\?"
)
_RATIO_TARGETS = re.compile(
    rf"Стрелок стреляет по одному разу по каждой из (?P<n>{CASED}) одинаковых мишеней\. Вероятность поразить мишень каждым отдельным выстрелом равна (?P<p>{NUMBER})\. Во сколько раз вероятность события «стрелок поразит ровно (?P<k>{COUNT}) мишени» больше вероятности события «стрелок поразит ровно (?P<other>{COUNT}) мишени»\?"
)
_RATIO_MACHINES = re.compile(
    rf"(?:Мастер|Компания) обслуживает (?P<n>\d+) (?:станков|серверов)\. Вероятность (?:поломки одного станка|отключения одного сервера) в течение дня равна (?P<p>{RATIONAL})\. Во сколько раз вероятность события «в течение дня ровно (?P<k>{COUNT}) (?:станка|сервер) потребуют ремонта» больше, чем вероятность события «в течение дня ровно (?P<other>{COUNT}) (?:станка|сервера) потребуют ремонта»[?.]"
)
_TWO_SHOTS = re.compile(
    rf"Стрелок стреляет по (?P<n>{CASED}) одинаковым мишеням\. На каждую мишень дается не более двух выстрелов, и известно, что вероятность поразить мишень каждым отдельным выстрелом равна (?P<p>{NUMBER})\. (?P<question>Во сколько раз вероятность события «стрелок поразит ровно (?P<a>{COUNT}) мишен(?:и|ей)» больше вероятности события «стрелок поразит ровно (?P<b>{COUNT}) мишени»\?|Найдите отношение вероятностей событий «стрелок поразит ровно (?P<c>{COUNT}) мишеней» и «стрелок поразит ровно (?P<d>{COUNT}) мишени»\.)"
)


def _parse_basic(text, places):
    if _PHONE.fullmatch(text):
        return Trial(2, Fraction(1, 2), "sequence", 2, style="phone", places=places)
    if match := _VOLLEY.fullmatch(text):
        if len({match[k] for k in ("team", "a", "b", "c")}) != 4:
            raise UnsupportedCondition(
                "the three opponents and the selected team must be distinct"
            )
        return Trial(
            3,
            Fraction(1, 2),
            "sequence",
            1 if match["games"] == "вторую игру" else 2,
            style="volleyball",
            places=places,
        )
    if match := _BATTERIES.fullmatch(text):
        n = count(match["n"])
        if n != 2:
            raise UnsupportedCondition(
                "both batteries must refer to exactly two trials"
            )
        return Trial(
            n, 1 - checked(parse_rational(match["p"])), "sequence", n, places=places
        )
    if match := _SELLERS.fullmatch(text):
        n = count(match["n"])
        if n != count(match["all"]) or not (match["independent"] or match["ending"]):
            raise UnsupportedCondition(
                "the seller count or independence assumption is inconsistent"
            )
        return Trial(n, parse_rational(match["p"]), "sequence", n, places=places)
    if match := _LAMPS.fullmatch(text):
        return Trial(
            {"двумя": 2, "тремя": 3}[match["n"]],
            1 - checked(parse_rational(match["p"])),
            "any",
            places=places,
        )
    if match := _TERMINALS.fullmatch(text):
        return Trial(
            2,
            1 - checked(parse_rational(match["p"])),
            "any",
            style="three-methods",
            places=places,
        )
    if match := _TERMINAL_DAY.fullmatch(text):
        return Trial(2, 1 - checked(parse_rational(match["p"])), "any", places=places)
    return None


def _parse_fixed(text, places):
    if match := _BIATHLON.fullmatch(text):
        n, k = count(match["n"]), count(match["k"])
        m = count(match["m"]) if match["m"] else 1
        if k + m != n:
            raise UnsupportedCondition(
                "fixed successes and failures must fill every trial"
            )
        return Trial(n, parse_rational(match["p"]), "sequence", k, places=places)
    if match := _TARGETS.fullmatch(text):
        n, k, m = (
            cardinal(match["n"]),
            count(match["k"]) if match["k"] else 1,
            count(match["m"]),
        )
        if k + m != n:
            raise UnsupportedCondition(
                "the fixed shooting order has an inconsistent length"
            )
        return Trial(n, parse_rational(match["p"]), "sequence", k, places=places)
    if match := _TARGETS_SHORT.fullmatch(text):
        n, m = int(match["n"]), int(match["m"])
        if 1 + m != n:
            raise UnsupportedCondition(
                "the first and remaining targets do not cover all targets"
            )
        return Trial(
            n, 1 - checked(parse_rational(match["p"])), "sequence", 1, places=places
        )
    if match := _LIGHT.fullmatch(text):
        return Trial(4, parse_rational(match["p"]), "sequence", 2, places=places)
    return None


def _parse_stopping(text, places):
    if match := _HIT.fullmatch(text):
        return Trial(
            2, parse_rational(match["p"]), "any", style="stopped", places=places
        )
    if match := _HIT_LIMIT.fullmatch(text):
        return Trial(
            int(match["n"]),
            parse_rational(match["p"]),
            "any",
            style="stopped",
            places=places,
        )
    if match := _SMS.fullmatch(text):
        return Trial(
            cardinal(match["n"]),
            parse_rational(match["p"]),
            "any",
            style="sms",
            places=places,
        )
    return None


def _parse_ratio(text, places):
    if match := _RATIO_COIN.fullmatch(text):
        a, b = count(match["k"]), count(match["other"])
        if match["direction"] == "меньше":
            a, b = b, a
        return Trial(
            int(match["n"]), Fraction(1, 2), "ratio", a, b, "coin-ratio", places
        )
    match = _RATIO_TARGETS.fullmatch(text) or _RATIO_MACHINES.fullmatch(text)
    if match:
        return Trial(
            cardinal(match["n"]),
            parse_rational(match["p"]),
            "ratio",
            count(match["k"]),
            count(match["other"]),
            places=places,
        )
    if match := _TWO_SHOTS.fullmatch(text):
        p = checked(parse_rational(match["p"]))
        return Trial(
            cardinal(match["n"]),
            1 - (1 - p) ** 2,
            "ratio",
            count(match["a"] or match["c"]),
            count(match["b"] or match["d"]),
            "two-shots",
            places,
            p,
        )
    return None


def parse(text):
    text, places = rounding(normalize(text))
    for parser in (_parse_basic, _parse_fixed, _parse_stopping, _parse_ratio):
        case = parser(text, places)
        if case is not None:
            return case
    raise UnsupportedCondition("unsupported complete independent-trial condition")


def binomial(n, k, p):
    return Fraction(comb(n, k)) * p**k * (1 - p) ** (n - k)


def _any(case, p, q):
    n = case.n
    value = 1 - q**n
    complement = (
        "<p>Вероятность неудачи в одной попытке равна q=1−p. Независимость позволяет перемножить вероятности неудач. Требуемое событие противоположно всем неудачам:</p>"
        + line(rf"P=1-q^{{{n}}}=1-({fmt(q)})^{{{n}}}")
    )
    if case.style in ("stopped", "sms"):
        html = (
            "<p>Первый успех может наступить на одной из указанных попыток. Эти события несовместны, поэтому складываем их вероятности:</p>"
            + line(rf"P=\sum_{{j=1}}^{{{n}}}q^{{j-1}}p")
        )
        html += line(
            "P=" + "+".join(rf"({fmt(q)})^{{{j}}}\cdot {fmt(p)}" for j in range(n))
        )
        if case.style == "stopped":
            html += (
                "<p>Другой способ: рассмотрим потенциальные попадания в каждом из независимых выстрелов, включая тот, который при раннем попадании уже не потребуется. Для двух выстрелов формула суммы событий имеет вид:</p>"
                if n == 2
                else "<p>Потенциальные результаты всех допустимых попыток независимы; событие успеха является их объединением:</p>"
            )
            html += (
                line(rf"P=2p-p^2=2\cdot {fmt(p)}-({fmt(p)})^2")
                if n == 2
                else line(rf"P=1-(1-p)^{{{n}}}")
            )
        return value, html + complement
    html = complement
    if case.style in ("three-methods", "restaurant"):
        html += (
            "<p>Способ 2. События исправности двух автоматов совместны и независимы. Применим формулу вероятности их объединения:</p>"
            + line(rf"P=p+p-p^2={fmt(p)}+{fmt(p)}-({fmt(p)})^2")
        )
        if case.style == "restaurant":
            html += (
                "<p>Способ 3. Нужная комбинация появляется либо в первой попытке, либо после первой неудачи во второй. Эти события несовместны:</p>"
                + line(rf"P=p+qp={fmt(p)}+{fmt(q)}\cdot {fmt(p)}")
            )
            return value, html
        html += (
            "<p>Способ 3. Разобьём успех на три несовместных случая: исправен только первый автомат, только второй или оба:</p>"
            + line(
                rf"P=pq+qp+p^2={fmt(p)}\cdot {fmt(q)}+{fmt(q)}\cdot {fmt(p)}+({fmt(p)})^2"
            )
        )
    return value, html


def _ratio(case, p, q, html):
    n = case.n
    if case.shot_p is not None:
        shot = case.shot_p
        html = (
            "<p>Мишень поражается либо первым выстрелом, либо после первого промаха вторым:</p>"
            + line(rf"p={fmt(shot)}+(1-{fmt(shot)})\cdot {fmt(shot)}={fmt(p)}")
            + html
        )
    a, b = binomial(n, case.k, p), binomial(n, case.other, p)
    if b == 0:
        raise UnsupportedCondition("the denominator probability of a ratio is zero")
    value = a / b
    html += (
        "<p>Используем формулу Бернулли для каждого точного числа успехов, затем найдём отношение:</p>"
        + line(r"P_n(k)=C_n^k p^kq^{n-k}")
    )
    for k, v in ((case.k, a), (case.other, b)):
        html += line(
            rf"P_{{{n}}}({k})=C_{{{n}}}^{{{k}}}({fmt(p)})^{{{k}}}({fmt(q)})^{{{n - k}}}"
        ) + line(rf"P_{{{n}}}({k})={fmt(v)}")
    html += line(
        rf"R=\frac{{P_{{{n}}}({case.k})}}{{P_{{{n}}}({case.other})}}=\frac{{{fmt(a)}}}{{{fmt(b)}}}"
    )
    if case.style == "coin-ratio":
        html += (
            "<p>Другой способ: все последовательности монеты равновозможны. Общий знаменатель 2^n сокращается, поэтому достаточно отношения чисел подходящих последовательностей:</p>"
            + line(
                rf"R=\frac{{C_{{{n}}}^{{{case.k}}}}}{{C_{{{n}}}^{{{case.other}}}}}=\frac{{{comb(n, case.k)}}}{{{comb(n, case.other)}}}"
            )
        )
    return result(value, html, case.places, "R")


def render(case):
    n, p = case.n, checked(case.p)
    q = 1 - p
    if not 1 <= n <= 100 or not 0 <= case.k <= n or not 0 <= case.other <= n:
        raise UnsupportedCondition("trial counts are outside the supported range")
    html = "<p>Обозначим вероятность успеха через p, а неудачи — через q:</p>" + line(
        rf"p={fmt(p)},\quad q=1-p={fmt(q)}"
    )
    if case.style == "phone":
        html = (
            "<p>Среди цифр от 0 до 9 пять четных (включая 0) и пять нечетных. Каждое из двух указанных мест независимо удовлетворяет условию с вероятностью 1/2.</p>"
            + html
        )
    if case.style == "volleyball":
        html = (
            "<p>Для каждой игры честный жребий даёт указанную команду с вероятностью 1/2. Вопрос фиксирует, в каких играх она должна выиграть жребий, а в каких — проиграть.</p>"
            + html
        )
    if case.kind == "ratio":
        return _ratio(case, p, q, html)
    if case.kind == "sequence":
        value = p**case.k * q ** (n - case.k)
        if case.k == n:
            html += (
                "<p>Все испытания должны завершиться успехом. По независимости перемножаем вероятности:</p>"
                + line(rf"P=p^{{{n}}}=({fmt(p)})^{{{n}}}")
            )
        else:
            html += (
                "<p>Порядок результатов задан условием. Перемножаем вероятности указанных успехов и неудач; переставлять их не требуется:</p>"
                + line(
                    rf"P=p^{{{case.k}}}q^{{{n - case.k}}}=({fmt(p)})^{{{case.k}}}({fmt(q)})^{{{n - case.k}}}"
                )
            )
    elif case.kind == "any":
        value, methods = _any(case, p, q)
        html += methods
    else:
        raise UnsupportedCondition("unsupported independent-trial event")
    return result(value, html, case.places)


def build_context_repair_plan(context):
    _, condition, answer_section, solution, text = require_content(context)
    answer, html = render(parse(text))
    return finish(condition, answer_section, solution, answer, html)
