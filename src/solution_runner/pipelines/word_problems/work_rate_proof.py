"""Parent time equations for manufacturing and reservoir filling rates."""

from ..probability.common import line
from .math_common import fraction as frac
from .math_common import number as n
from .motion_proof import conversions, quadratic_steps


def proof(a):
    q, v = a.question, a.question.values
    symbol = q.symbol
    workers = q.kind == "work_worker_rates"
    fast = symbol if q.target_fast else symbol + "+" + n(v["gap"])
    slow = symbol + "-" + n(v["gap"]) if q.target_fast else symbol
    if workers:
        who = "первый" if q.target_fast else "второй"
        other = "второй" if q.target_fast else "первый"
        html = f"<p>Обозначим {symbol} — число деталей, которые изготавливает за час {who} рабочий. Тогда {other} рабочий за час изготавливает:</p>"
    else:
        who = "вторая" if q.target_fast else "первая"
        other = "первая" if q.target_fast else "вторая"
        html = f"<p>Пусть {symbol} литров воды в минуту пропускает {who} труба, тогда {other} труба пропускает:</p>"
    html += line(slow if q.target_fast else fast)
    html += line(symbol + ">" + (n(v["gap"]) if q.target_fast else "0"))
    html += conversions(q)
    subject = "Первый рабочий затратил" if workers else "Вторая труба затратила"
    html += f"<p>Время выполнения работы равно объёму работы, делённому на производительность. {subject} на свою работу меньше времени:</p>"
    t_fast, t_slow = frac(n(v["fast_amount"]), fast), frac(n(v["slow_amount"]), slow)
    delay = n(v["delay"])
    if not workers and q.target_fast and v["fast_amount"] != v["slow_amount"]:
        equation = t_slow + "=" + t_fast + "+" + delay
    elif (workers and not q.target_fast) or v["fast_amount"] != v["slow_amount"]:
        equation = t_fast + "+" + delay + "=" + t_slow
    else:
        equation = t_slow + "-" + t_fast + "=" + delay
    html += line(equation)
    return html + quadratic_steps(a, quantities="времени и производительностей")
