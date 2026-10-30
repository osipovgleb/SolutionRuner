"""Waiting for successes and collecting distinct equally likely outcomes."""

import re
from fractions import Fraction

from .common import (
    COUNT,
    NUMBER,
    UnsupportedCondition,
    count,
    fmt,
    line,
    plan,
    probability,
    result,
)

_COIN = re.compile(
    rf"Монету подбрасывают до тех пор, пока орел не выпадет (?P<k>{COUNT}) раза\s*\(не обязательно подряд\)\. Найдите математическое ожидание числа бросков\."
)
_DIE = re.compile(
    rf"Игральный кубик бросают до тех пор, пока (?:(?:шестерка|грань с шестью очками) не выпадет (?P<k>{COUNT}) раза|(?P<even>{COUNT}) раза не выпадет четное число очков), не обязательно подряд\. Найдите математическое ожидание случайной величины «число сделанных бросков»\."
)
_SHOOTER = re.compile(
    rf"Стрелок в тире стреляет по мишеням\. По каждой он стреляет до тех пор, пока не поразит ее\. При каждом отдельном выстреле стрелок попадает в мишень с вероятностью (?P<p>{NUMBER})\. Сколько потребуется выстрелов, чтобы поразить (?P<k>{COUNT}) мишен(?:и|ей)\? Найдите математическое ожидание этой случайной величины\."
)
_STUDENT = re.compile(
    rf"Студент сдает зачет по теории вероятностей до тех пор, пока не решит какую-нибудь задачу\. Вероятность решения любой задачи этим студентом равна (?P<p>{NUMBER})\. Сколько задач в среднем он получит\?"
)
_SIMPLE = {
    "Сколько раз в среднем нужно бросить монету, чтобы на ней выпал орел?": Fraction(
        1, 2
    ),
    "Сколько раз нужно в среднем бросить кубик, чтобы на нем выпала шестерка?": Fraction(
        1, 6
    ),
}
_BOTH = "Симметричную монету бросают до тех пор, пока решка и орел не выпадут хотя бы по одному разу. Найдите математическое ожидание случайной величины «число сделанных бросков»."
_DICE_COLLECT = re.compile(
    r"Правильную игральную кость бросают до тех пор, пока (?P<faces>грани с [1-6](?:, [1-6])*(?: и [1-6])? очками|каждая грань) не выпад(?:ет|ут) хотя бы по одному разу\. Найдите математическое ожидание случайной величины «число сделанных бросков»\."
)
_TOYS = re.compile(
    r"В киндер-сюрпризах встречаются игрушки из коллекции (?P<kind>бегемотов|принцесс)\. Всего в коллекции (?P<n>\d+) (?P<items>различных бегемотов|разных принцесс), причем все они встречаются в киндер-сюрпризах одинаково часто\. (?P<target>Среди них есть бегемот в кепке|Среди принцесс есть Золушка)\. Первоклассни(?:к|ца) покупает киндер-сюрпризы, а игрушки из них кладет в ящик стола\. Сколько будет куплено киндер-сюрпризов к моменту, когда в столе окажутся (?P<copies>два одинаковых бегемота в кепке|две Золушки)\? Найдите математическое ожидание этой случайной величины\."
)
_CARS = re.compile(
    r"В киндер-сюрпризах встречаются игрушки из коллекции автомобилей\. [ВB]сего в коллекции (?P<n>\d+) автомобильчиков, причем все они встречаются одинаково часто\. Второклассник А\. покупает киндер-сюрпризы\. Сколько будет куплено киндер-сюрпризов к моменту, когда у А\. образуется полная коллекция, в которой есть все автомобильчики\? Найдите математическое ожидание этой случайной величины\."
)


def successes(k, p, *, proof=False):
    probability(p, positive=True)
    if k < 1:
        raise UnsupportedCondition("the number of required successes must be positive")
    html = "<p>Число испытаний до первого успеха имеет геометрическое распределение. Его математическое ожидание обратно вероятности успеха:</p>"
    html += line(r"E(T)=\frac{1}{p}") + line(
        rf"E(T)=\frac{{1}}{{{fmt(p)}}}={fmt(1 / p)}"
    )
    html += "<p>До каждого следующего успеха ожидаем столько же испытаний. По линейности математического ожидания складываем ожидания отдельных этапов:</p>"
    html += line(rf"E(X)={k}\cdot E(T)={k}\cdot {fmt(1 / p)}={fmt(k / p)}")
    if proof:
        html += "<p>Обоснование формулы. При q=1−p вероятность первого успеха на k-м шаге равна q^(k−1)p. Для |q|&lt;1 продифференцируем сумму геометрической прогрессии:</p>"
        html += line(r"\sum_{k=0}^{\infty}q^k=\frac{1}{1-q}")
        html += line(r"\sum_{k=1}^{\infty}kq^{k-1}=\frac{1}{(1-q)^2}")
        html += line(r"E(T)=p\sum_{k=1}^{\infty}kq^{k-1}=\frac{p}{(1-q)^2}=\frac{1}{p}")
        html += "<p>Если ждём r успехов, вероятность остановки на k-м испытании равна числу способов разместить r−1 предыдущих успехов, умноженному на вероятность каждого порядка:</p>"
        html += line(r"P(X=k)=C_{k-1}^{r-1}p^r(1-p)^{k-r},\quad k\ge r")
        html += (
            "<p>Это согласуется с разбиением ожидания на r последовательных этапов.</p>"
        )
    return result(k / p, html)


def collector(n, targets):
    if not 1 <= targets <= n or n > 100:
        raise UnsupportedCondition(
            "the collection must have between one and 100 equally likely kinds"
        )
    terms = [Fraction(n, k) for k in range(targets, 0, -1)]
    html = "<p>Разобьём сбор на этапы между появлениями новых нужных видов. Когда ещё не собраны j нужных видов из n равновозможных, вероятность нового вида равна j/n. Среднее число попыток до него равно n/j:</p>"
    html += line(r"E(T_j)=\frac{1}{j/n}=\frac{n}{j}")
    html += (
        "<p>По линейности математического ожидания складываем ожидания всех этапов:</p>"
    )
    html += line(
        "E(X)=" + "+".join(rf"\frac{{{n}}}{{{k}}}" for k in range(targets, 0, -1))
    )
    html += line("E(X)=" + "+".join(fmt(x) for x in terms))
    return result(sum(terms), html)


def solve(text, tables):
    if tables:
        raise UnsupportedCondition("a waiting-time condition must not contain a table")
    if match := _COIN.fullmatch(text):
        return successes(count(match["k"]), Fraction(1, 2), proof=True)
    if match := _DIE.fullmatch(text):
        return successes(
            count(match["k"] or match["even"]),
            Fraction(1, 2) if match["even"] else Fraction(1, 6),
        )
    if match := _SHOOTER.fullmatch(text):
        return successes(count(match["k"]), Fraction(match["p"].replace(",", ".")))
    if match := _STUDENT.fullmatch(text):
        return successes(1, Fraction(match["p"].replace(",", ".")))
    if text in _SIMPLE:
        return successes(1, _SIMPLE[text])
    if text == _BOTH:
        answer, html = collector(2, 2)
        return (
            answer,
            "<p>Первый бросок даёт одну из сторон. После него ждём появления другой стороны:</p>"
            + html,
        )
    if match := _DICE_COLLECT.fullmatch(text):
        faces = (
            list(map(int, re.findall("[1-6]", match["faces"])))
            if match["faces"] != "каждая грань"
            else list(range(1, 7))
        )
        if len(set(faces)) != len(faces):
            raise UnsupportedCondition("the collection repeats a die face")
        return collector(6, len(faces))
    if match := _CARS.fullmatch(text):
        n = int(match["n"])
        return collector(n, n)
    if match := _TOYS.fullmatch(text):
        coherent = (
            match["kind"] == "бегемотов"
            and match["items"] == "различных бегемотов"
            and match["target"].startswith("Среди них")
            and match["copies"].startswith("два")
        ) or (
            match["kind"] == "принцесс"
            and match["items"] == "разных принцесс"
            and match["target"].startswith("Среди принцесс")
            and match["copies"] == "две Золушки"
        )
        if not coherent:
            raise UnsupportedCondition(
                "the named toy must belong to the declared collection"
            )
        return successes(2, Fraction(1, int(match["n"])))
    raise UnsupportedCondition("unsupported complete waiting-time condition")


def build_context_repair_plan(context):
    return plan(context, solve)
