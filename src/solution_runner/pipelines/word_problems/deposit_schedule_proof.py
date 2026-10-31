"""Parent annual recurrence, original-capital equation and comparison of products."""

from ..probability.common import line
from .deposit_schedules import X, balances
from .math_common import number as n

UNITS = {1: r"\text{ руб.}", 1000: r"\text{ тыс. руб.}", 1000000: r"\text{ млн руб.}"}


def convert(a, value):
    q = a.question
    if q.unit == q.output_unit:
        return ""
    return "<p>Переведём полученную сумму в единицы, указанные в вопросе:</p>" + line(
        n(value) + UNITS[q.unit] + "=" + n(a.result) + UNITS[q.output_unit]
    )


def factor(a):
    q = 1 + a.rate / 100
    return line(r"k=1+\frac{" + n(a.rate) + "}{100}=" + n(q))


def forward(a):
    q = a.question
    k = 1 + a.rate / 100
    html = (
        "<p>Проценты начисляются в конце года. Пополнение или снятие происходит в начале следующего года, поэтому сначала изменим сумму вклада, а затем начислим проценты:</p>"
        + factor(a)
    )
    html += line("S_1=" + n(a.capital) + r"\cdot" + n(k) + "=" + n(a.balances[0]))
    if q.periods > 1:
        html += line(
            r"S_j=(S_{j-1}+(" + n(q.flow) + r"))k,\qquad j=2,\ldots," + str(q.periods)
        )
    for year in range(2, q.periods + 1):
        previous = a.balances[year - 2]
        html += line(
            "S_{"
            + str(year)
            + "}=("
            + n(previous)
            + "+("
            + n(q.flow)
            + r"))\cdot"
            + n(k)
            + "="
            + n(previous + q.flow)
            + r"\cdot"
            + n(k)
            + "="
            + n(a.balances[year - 1])
        )
    html += "<p>Таким образом, в конце указанного срока получим:</p>" + line(
        "S_{" + str(q.periods) + "}=" + n(a.balances[-1]) + UNITS[q.unit]
    )
    return html + convert(a, a.balances[-1])


def initial(a):
    q = a.question
    k = 1 + a.rate / 100
    html = (
        "<p>Пусть x — первоначальная сумма вклада в указанных денежных единицах. Каждый год проценты начисляются после пополнения, а в первом году пополнения нет:</p>"
        + factor(a)
    )
    expression = "x"
    for year in range(1, q.periods + 1):
        expression = (
            ("(" + expression + "+(" + n(q.flow) + "))" if year > 1 else expression)
            + r"\cdot"
            + n(k)
        )
    html += line(expression + "=" + n(q.final))
    polynomial = balances(X, (a.rate,) * q.periods, q.flow)[-1]
    aa, bb = polynomial.coeff(X), polynomial.subs(X, 0)
    html += "<p>Раскроем скобки и решим линейное уравнение относительно первоначальной суммы:</p>"
    html += line(n(aa) + "x+(" + n(bb) + ")=" + n(q.final))
    html += line(n(aa) + "x=" + n(q.final) + "-(" + n(bb) + ")=" + n(q.final - bb))
    html += line(
        "x="
        + r"\frac{"
        + n(q.final - bb)
        + "}{"
        + n(aa)
        + "}="
        + n(a.capital)
        + UNITS[q.unit]
    )
    return html + convert(a, a.capital)


def rate(a):
    q = a.question
    k = 1 + a.rate / 100
    html = "<p>Пусть k — годовой множитель роста. Проценты капитализируются ежегодно, поэтому за указанный срок первоначальная сумма умножается на степень k:</p>"
    html += line(r"k=1+\frac{r}{100}>0")
    html += line(n(a.capital) + "k^{" + str(q.periods) + "}=" + n(q.final))
    ratio = q.final / a.capital
    html += line(
        "k^{"
        + str(q.periods)
        + "}="
        + r"\frac{"
        + n(q.final)
        + "}{"
        + n(a.capital)
        + "}="
        + n(ratio)
    )
    html += "<p>Годовой множитель положителен. Найдём его и восстановим процентную ставку:</p>"
    html += line(
        "k=(" + n(ratio) + ")^{" + r"\frac{1}{" + str(q.periods) + "}}=" + n(k)
    )
    return html + line("r=100(k-1)=100(" + n(k) + "-1)=" + n(a.result))


def compare(a):
    q = a.question
    fixed = 1 + a.rate / 100
    rates = [q.first + i * q.step for i in range(q.periods)]
    factors = [1 + r / 100 for r in rates]
    html = (
        "<p>При первом варианте ставка неизменна. Найдём сумму вклада после ежегодной капитализации:</p>"
        + factor(a)
    )
    html += line(
        "S_1="
        + n(a.capital)
        + r"\cdot("
        + n(fixed)
        + ")^{"
        + str(q.periods)
        + "}="
        + n(a.capital)
        + r"\cdot"
        + n(fixed**q.periods)
        + "="
        + n(a.balances[-1])
        + UNITS[q.unit]
    )
    html += "<p>Во втором варианте ежегодная ставка увеличивается на указанное число процентных пунктов. Найдём ставки по годам и последовательно применим годовые множители:</p>"
    html += line(
        r"(r_1,\ldots,r_{"
        + str(q.periods)
        + r"})=("
        + (";".join(n(r) for r in rates))
        + r")\%"
    )
    html += line(
        "S_2="
        + n(a.capital)
        + r"\cdot"
        + r"\cdot".join("(" + n(f) + ")" for f in factors)
        + "="
        + n(a.alternative[-1])
        + UNITS[q.unit]
    )
    winner = "первом" if a.balances[-1] > a.alternative[-1] else "втором"
    high, low = (
        max(a.balances[-1], a.alternative[-1]),
        min(a.balances[-1], a.alternative[-1]),
    )
    html += "<p>Сумма вклада больше при " + winner + " варианте. Найдём разницу:</p>"
    html += line(
        r"\Delta S=" + n(high) + "-(" + n(low) + ")=" + n(high - low) + UNITS[q.unit]
    )
    return html + convert(a, high - low)


def proof(a):
    return {"forward": forward, "initial": initial, "rate": rate, "compare": compare}[
        a.question.kind
    ](a)
