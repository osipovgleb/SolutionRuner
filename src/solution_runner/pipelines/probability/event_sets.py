"""Complementary, nested and disjoint probability events with checked boundaries."""

import re

from solution_runner.pipelines.core.numbers import parse_rational

from .bernoulli import checked, fmt, result
from .common import (
    NUMBER,
    UnsupportedCondition,
    finish,
    line,
    normalize,
    require_content,
)

_TEMP = re.compile(
    rf"Вероятность того, что в случайный момент времени температура тела здорового человека окажется ниже чем (?P<a>{NUMBER})°C, равна (?P<p>{NUMBER})\. Найдите вероятность того, что в случайный момент времени у здорового человека температура окажется (?P<b>{NUMBER})°C или выше\."
)
_BEARING = re.compile(
    rf"При изготовлении подшипников диаметром (?P<d>{NUMBER}) мм вероятность того, что диаметр будет отличаться от заданного не больше,? чем на (?P<e>{NUMBER}) мм, равна (?P<p>{NUMBER})\. Найдите вероятность того, что случайный подшипник будет иметь диаметр меньше,? чем (?P<lo>{NUMBER}) мм,? или больше,? чем (?P<hi>{NUMBER}) мм\."
)
_LIFETIME = re.compile(
    rf"Вероятность того, что новый [а-я-]+(?: [а-я-]+)? прослужит больше года, равна (?P<p>{NUMBER})\. Вероятность того, что он прослужит больше двух лет, равна (?P<q>{NUMBER})\. Найдите вероятность того, что он прослужит меньше двух лет, но больше года\."
)
_BUS = re.compile(
    rf"Из районного центра в деревню ежедневно ходит автобус\. Вероятность того, что (?:в понедельник )?в автобусе окажется меньше (?P<hi>\d+) пассажиров, равна (?P<p>{NUMBER})\. Вероятность того, что окажется меньше (?P<lo>\d+) пассажиров, равна (?P<q>{NUMBER})\. Найдите вероятность того, что число пассажиров будет от (?P<from>\d+) до (?P<to>\d+)\."
)
_EXAM = re.compile(
    rf"На экзамене по геометрии школьник отвечает на один вопрос из списка экзаменационных вопросов\. Вероятность того, что это вопрос (?:по теме|на тему) «(?P<a>[^«»]+)», равна (?P<p>{NUMBER})\. Вероятность того, что это вопрос (?:по теме|на тему) «(?P<b>[^«»]+)», равна (?P<q>{NUMBER})\. Вопросов, которые одновременно относятся к этим двум темам, нет\. Найдите вероятность того, что на экзамене школьнику достанется вопрос по одной из этих двух тем\."
)
_BREAD = re.compile(
    rf"При выпечке хлеба производится контрольное взвешивание свежей буханки\. Известно, что вероятность того, что масса окажется меньше,? чем (?P<hi>{NUMBER}) г, равна (?P<p>{NUMBER})\. Вероятность того, что масса окажется больше,? чем (?P<lo>{NUMBER}) г, равна (?P<q>{NUMBER})\. Найдите вероятность того, что масса буханки больше,? чем (?P<a>{NUMBER}) г, но меньше,? чем (?P<b>{NUMBER}) г\."
)
_SEEDS = re.compile(
    rf"Семена подсолнечника расфасовывают в пакеты по 1 кг\. Вероятность того, что в случайно выбранном пакете масса семян окажется меньше,? чем (?P<hi>{NUMBER}) г, равна (?P<p>{NUMBER})\. Вероятность того, что масса окажется больше,? чем (?P<lo>{NUMBER}) г, равна (?P<q>{NUMBER})\. Найдите вероятность того, что масса семян в этом пакете окажется в интервале от (?P<a>{NUMBER}) г до (?P<b>{NUMBER}) г\."
)


def _complement(p, description):
    html = (
        "<p>"
        + description
        + " События противоположны и вместе образуют достоверное событие:</p>"
        + line(r"P(A)+P(\overline{A})=1")
        + line(r"P(\overline{A})=1-P(A)")
        + line(rf"P(\overline{{A}})=1-{fmt(p)}")
    )
    return result(1 - p, html)


def _interval(match, complement):
    lo, hi, a, b = (parse_rational(match[k]) for k in ("lo", "hi", "a", "b"))
    p, q = checked(parse_rational(match["p"])), checked(parse_rational(match["q"]))
    if not lo < hi or a != lo or b != hi or p + q < 1:
        raise UnsupportedCondition(
            "the interval boundaries or tail probabilities are inconsistent"
        )
    if complement:
        html = (
            "<p>Вне промежутка находятся два несовместных события: масса не больше нижней границы либо не меньше верхней. Их вероятности найдём через противоположные события:</p>"
            + line(rf"P(X\le {fmt(lo)})=1-{fmt(q)}={fmt(1 - q)}")
            + line(rf"P(X\ge {fmt(hi)})=1-{fmt(p)}={fmt(1 - p)}")
            + line(rf"P({fmt(lo)}<X<{fmt(hi)})=1-({fmt(1 - q)}+{fmt(1 - p)})")
        )
    else:
        html = (
            "<p>События «масса меньше верхней границы» и «масса больше нижней границы» совместны. Их объединение достоверно, а пересечение — искомый промежуток:</p>"
            + line(r"P(A\cup B)=P(A)+P(B)-P(A\cap B)")
            + line(r"P(A\cap B)=P(A)+P(B)-1")
            + line(rf"P(A\cap B)={fmt(p)}+{fmt(q)}-1")
        )
    return result(p + q - 1, html)


def solve(text):
    text = (
        normalize(text)
        .replace(r"\,^{\circ}\mathrm{C}", "°C")
        .replace("°С", "°C")
        .replace("{,}", ",")
    )
    text = re.sub(r"\s*°C", "°C", text)
    if match := _TEMP.fullmatch(text):
        if parse_rational(match["a"]) != parse_rational(match["b"]):
            raise UnsupportedCondition(
                "the complementary temperature events use different thresholds"
            )
        return _complement(
            checked(parse_rational(match["p"])),
            "Температура либо ниже указанной границы, либо равна ей или выше.",
        )
    if match := _BEARING.fullmatch(text):
        d, e, lo, hi = (parse_rational(match[k]) for k in ("d", "e", "lo", "hi"))
        if e < 0 or lo != d - e or hi != d + e:
            raise UnsupportedCondition(
                "the outside diameter interval must complement the stated tolerance"
            )
        return _complement(
            checked(parse_rational(match["p"])),
            "Диаметр либо отклоняется от заданного не больше допуска, либо лежит строго вне этого интервала.",
        )
    if match := _LIFETIME.fullmatch(text):
        p, q = checked(parse_rational(match["p"])), checked(parse_rational(match["q"]))
        if p < q:
            raise UnsupportedCondition("longer service life cannot be more probable")
        html = (
            "<p>Срок службы моделируется непрерывной величиной, поэтому вероятность отказа ровно через два года равна нулю. Событие «больше года» разбивается на срок между одним и двумя годами и срок больше двух лет:</p>"
            + line(r"P(T>1)=P(1<T<2)+P(T>2)")
            + line(r"P(1<T<2)=P(T>1)-P(T>2)")
            + line(rf"P(1<T<2)={fmt(p)}-{fmt(q)}")
        )
        return result(p - q, html)
    if match := _BUS.fullmatch(text):
        lo, hi, a, b = (int(match[k]) for k in ("lo", "hi", "from", "to"))
        p, q = checked(parse_rational(match["p"])), checked(parse_rational(match["q"]))
        if not 0 <= lo < hi or a != lo or b != hi - 1 or q > p:
            raise UnsupportedCondition(
                "the discrete passenger interval is not the difference of the stated tails"
            )
        html = (
            "<p>Число пассажиров целое. Меньше верхней границы — значит либо меньше нижней, либо в указанном включительном промежутке. События несовместны:</p>"
            + line(rf"P(X<{hi})=P(X<{lo})+P({lo}\le X\le {hi - 1})")
            + line(rf"P({lo}\le X\le {hi - 1})={fmt(p)}-{fmt(q)}")
        )
        return result(p - q, html)
    if match := _EXAM.fullmatch(text):
        p, q = checked(parse_rational(match["p"])), checked(parse_rational(match["q"]))
        if match["a"] == match["b"] or p + q > 1:
            raise UnsupportedCondition(
                "the disjoint exam topics are not a consistent event pair"
            )
        html = (
            "<p>Вопрос не может относиться к обеим темам сразу. Для суммы несовместных событий складываем вероятности:</p>"
            + line(r"P(A\cup B)=P(A)+P(B)")
            + line(rf"P(A\cup B)={fmt(p)}+{fmt(q)}")
        )
        return result(p + q, html)
    if match := _BREAD.fullmatch(text):
        return _interval(match, False)
    if match := _SEEDS.fullmatch(text):
        return _interval(match, True)
    raise UnsupportedCondition("unsupported complete event-set condition")


def build_context_repair_plan(context):
    _, condition, answer_section, solution, text = require_content(context)
    answer, html = solve(text)
    return finish(condition, answer_section, solution, answer, html)
