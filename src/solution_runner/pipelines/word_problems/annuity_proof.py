"""Keep the chronological, general-formula, table and refinancing parent methods."""

from ..probability.common import line
from .math_common import fraction
from .math_common import number as n
from .motion_chase_proof import section
from .water_season_proof import inline as latex


def factor(a, symbol="k"):
    return line(symbol + r"=1+\frac{" + n(a.question.rate) + "}{100}=" + n(a.factor))


def two_years(a):
    s, x, k = a.capital / 1000, a.payment / 1000, a.factor
    html = "<p>Первоначальный долг выразим в тысячах рублей. После начисления процентов он увеличивается, затем первая выплата уменьшает его. Пусть x тыс. руб. — каждый из двух равных платежей:</p>"
    html += line(
        "S=" + n(s) + r",\qquad k=1+\frac{" + n(a.question.rate) + "}{100}=" + n(k)
    )
    html += line(n(s) + r"\cdot" + n(k) + "=" + n(s * k))
    html += line("S_1=" + n(s * k) + "-x")
    html += "<p>После второго начисления процентов весь оставшийся долг погашается вторым платежом, также равным x:</p>"
    html += line("(" + n(s * k) + "-x)\\cdot" + n(k) + "=x")
    html += line(n(s * k**2) + "-" + n(k) + "x=x")
    html += line(n(1 + k) + "x=" + n(s * k**2))
    html += line("x=" + fraction(n(s * k**2), n(1 + k)) + "=" + n(x))
    html += "<p>Сложим два платежа и переведём тысячи рублей в рубли:</p>"
    html += line(
        "2x=2\\cdot"
        + n(x)
        + "="
        + n(2 * x)
        + r"\text{ тыс. руб.}="
        + n(a.result)
        + r"\text{ руб.}"
    )
    return html


def general_two(a):
    k = a.factor
    html = "<p>Пусть сумма кредита равна S рублей, ставка составляет a процентов, а каждый платёж равен X рублей. После начисления процентов остаток умножается на коэффициент b:</p>"
    html += line(r"b=1+\frac{a}{100},\qquad S_1=Sb-X")
    html += line(r"S_2=S_1b-X=(Sb-X)b-X")
    html += line(r"S_2=Sb^2-(1+b)X=0")
    html += line(r"(1+b)X=Sb^2,\qquad X=\frac{Sb^2}{1+b}")
    html += "<p>Подставим сумму кредита и годовой множитель. Общая выплата равна двум одинаковым платежам:</p>"
    html += line("S=" + n(a.capital) + r",\qquad b=" + n(k))
    html += line(
        "2X=2\\cdot"
        + fraction(n(a.capital) + r"\cdot" + n(k**2), n(1 + k))
        + "="
        + n(a.result)
        + r"\text{ руб.}"
    )
    return html


def three_years(a):
    k, s = a.factor, a.capital
    weights = k**2 + k + 1
    html = "<p>Пусть S — сумма кредита в рублях, x — ежегодный платёж. Каждый год сначала начисляются проценты, затем вносится платёж. Запишем схему погашения:</p>"
    html += line("S=" + n(s)) + factor(a)
    html += line(r"k\bigl(k(kS-x)-x\bigr)-x=0")
    html += line(r"k^3S-k^2x-kx-x=0")
    html += line(r"(k^2+k+1)x=k^3S")
    html += line(r"x=\frac{k^3S}{k^2+k+1}")
    html += line(
        "x=" + fraction(n(k**3) + r"\cdot" + n(s), n(k**2) + "+" + n(k) + "+1")
    )
    html += line("x=" + fraction(n(k**3 * s), n(weights)) + "=" + n(a.payment))
    html += "<p>Общая сумма выплат равна трём ежегодным платежам:</p>"
    return html + line(
        "3x=3\\cdot" + n(a.payment) + "=" + n(a.result) + r"\text{ руб.}"
    )


def principal(a):
    k, x = a.factor, a.payment
    html = "<p>Пусть сумма кредита составляет S млн рублей, а ежегодная выплата равна x млн рублей. Долг на июль после очередной выплаты последовательно уменьшается до нуля:</p>"
    html += line("x=" + n(x)) + factor(a)
    html += line(r"S_0=S,\qquad S_1=kS-x")
    html += line(r"S_2=k(kS-x)-x=k^2S-(k+1)x")
    html += line(r"S_3=kS_2-x=k^3S-(k^2+k+1)x=0")
    html += "<p>Выразим сумму кредита. Используем сумму геометрической прогрессии:</p>"
    html += line(r"k^2+k+1=\frac{k^3-1}{k-1}")
    html += line(r"S=\frac{(k^2+k+1)x}{k^3}=\frac{(k^3-1)x}{k^3(k-1)}")
    html += line(
        "S="
        + fraction("(" + n(k**3) + "-1)\\cdot" + n(x), n(k**3) + r"\cdot" + n(k - 1))
        + "="
        + n(a.capital)
        + r"\text{ млн руб.}"
    )
    return html + line(n(a.capital) + r"\cdot1000000=" + n(a.result) + r"\text{ руб.}")


def refinancing(a):
    s, x, debt = a.capital / 1_000_000, a.payment / 1_000_000, a.debts[1] / 1_000_000
    k, r = a.factor, a.question.rate - a.question.new_rate
    html = "<p>Пусть x миллионов рублей составляла ежегодная выплата по первоначальному договору. Два одинаковых платежа должны полностью погасить долг:</p>"
    html += factor(a)
    html += line("(" + n(s) + r"\cdot" + n(k) + "-x)\\cdot" + n(k) + "-x=0")
    html += line(n(s * k**2) + "-(" + n(k) + "+1)x=0")
    html += line("x=" + fraction(n(s * k**2), n(k + 1)) + "=" + n(x))
    html += (
        "<p>Первую выплату сделали по договору. Найдём долг, оставшийся после неё:</p>"
    )
    html += line(
        "D=" + n(s) + r"\cdot" + n(k) + "-" + n(x) + "=" + n(debt) + r"\text{ млн руб.}"
    )
    html += "<p>Рефинансирование уменьшает только проценты за второй год. Экономия равна разности ставок, начисленной на оставшийся долг:</p>"
    html += line(
        r"\Delta r=" + n(a.question.rate) + "-" + n(a.question.new_rate) + "=" + n(r)
    )
    html += line(
        r"E=\frac{"
        + n(r)
        + r"}{100}\cdot"
        + n(debt)
        + "="
        + n(a.result / 1_000_000)
        + r"\text{ млн руб.}"
    )
    return html + line(
        "E="
        + n(a.result / 1_000_000)
        + r"\cdot1000000="
        + n(a.result)
        + r"\text{ руб.}"
    )


def affine(k, weights):
    return (
        n(k)
        + "S"
        + ("-" + (n(weights) if weights != 1 else "") + "x" if weights else "")
    )


def credit_table(a):
    html = "<table><tbody><tr>"
    for title in (
        "Год (номер года)",
        "Долг в январе (в руб.)",
        "Выплата (в руб.)",
        "Долг в июле (в руб.)",
    ):
        html += (
            '<th data-align="center" data-cell-tone="source-header" data-valign="middle">'
            + title
            + "</th>"
        )
    html += "</tr>"
    rows = [(str(a.question.year), "", "", latex("S"))]
    k, weights = a.factor, 0
    for j in range(1, 4):
        accrued = affine(k**j, weights * k)
        weights = weights * k + 1
        balance = affine(k**j, weights) + ("=0" if j == 3 else "")
        rows.append(
            (str(a.question.year + j), latex(accrued), latex("x"), latex(balance))
        )
    for row in rows:
        html += (
            "<tr>"
            + "".join(
                '<td data-align="center" data-valign="middle">' + cell + "</td>"
                for cell in row
            )
            + "</tr>"
        )
    return html + "</tbody></table>"


def table_method(a):
    k, s = a.factor, a.capital
    weights = k**2 + k + 1
    html = "<p>Пусть сумма кредита равна S рублей, а ежегодная выплата равна x рублей. Каждый январь долг увеличивается на указанную ставку, затем очередной платёж уменьшает его. Заполним таблицу:</p>"
    html += line("S=" + n(s)) + factor(a) + credit_table(a)
    html += "<p>Последняя строка таблицы даёт уравнение полного погашения. Найдём ежегодный платёж:</p>"
    html += line(affine(k**3, weights) + "=0")
    html += line(n(weights) + "x=" + n(k**3) + "S")
    html += line("x=" + fraction(n(k**3) + "S", n(weights)))
    html += line(
        "x=" + fraction(n(k**3) + r"\cdot" + n(s), n(weights)) + "=" + n(a.payment)
    )
    html += "<p>Сложим три одинаковых платежа:</p>"
    return html + line(
        "3x=3\\cdot" + n(a.payment) + "=" + n(a.result) + r"\text{ руб.}"
    )


def proof(a):
    if a.question.style == "grace":
        from .grace_proof import proof as grace_proof

        return section(grace_proof(a), "Решение")
    methods = {
        "two": two_years,
        "three": three_years,
        "principal": principal,
        "refinance": refinancing,
        "table": table_method,
    }
    html = section(methods[a.question.style](a), "Решение")
    if a.question.style == "two":
        html += section(general_two(a), "Приведём решение в общем случае.")
    return html
