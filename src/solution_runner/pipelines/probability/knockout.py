"""Meeting probability in a fair knockout tournament, including random byes."""

import re
from fractions import Fraction

from .bernoulli import fmt, result
from .common import UnsupportedCondition, finish, line, normalize, require_content

_STANDARD = "Турнир по настольному теннису проводится по олимпийской системе: игроки случайным образом разбиваются на игровые пары; проигравший в каждой паре выбывает из турнира, а победитель выходит в следующий тур, где встречается со следующим противником, который определен жребием. "
_BYES = "Турнир по настольному теннису проводится по олимпийской системе в несколько туров: если в туре участвует четное число игроков, то они разбиваются на случайные игровые пары. Если число игроков нечетно, то с помощью жребия выбираются случайные игровые пары, а один игрок остается без пары и не участвует в туре. Проигравший в каждой паре (ничья невозможна) выбывает из турнира, а победители и игрок без пары, если он есть, выходят в следующий тур, который проводится по таким же правилам. Так продолжается до тех пор, пока не останутся двое, которые играют между собой финальный тур, то есть последнюю партию, которая выявляет победителя турнира. "
_TAIL = re.compile(
    r"Всего в турнире участвует (?P<n>\d+) игрок(?:ов|а)?, все они играют одинаково хорошо, поэтому в каждой встрече вероятность выигрыша и поражения у каждого игрока равна 0[,.]5\. Среди игроков два друга [—–-] Иван и Алексей\. Какова вероятность того, что этим двоим в каком-то туре придется сыграть друг с другом\?"
)


def meeting_rounds(n):
    if not isinstance(n, int) or not 2 <= n <= 4096:
        raise UnsupportedCondition("supported tournaments have 2–4096 players")
    alive = Fraction(1)
    rows = []
    while n > 1:
        if n % 2:
            # Both play separately, or exactly one gets the single random bye.
            meet = Fraction(1, n)
            survive = Fraction(n - 3, 4 * n) + Fraction(1, n)
        else:
            meet = Fraction(1, n - 1)
            survive = Fraction(n - 2, 4 * (n - 1))
        rows.append((n, alive * meet))
        alive *= survive
        n = (n + 1) // 2
    return tuple(rows)


def build_context_repair_plan(context):
    _, condition, answer_section, solution, text = require_content(context)
    text = normalize(text)
    byes = text.startswith(_BYES)
    prefix = _BYES if byes else _STANDARD
    match = (
        _TAIL.fullmatch(text.removeprefix(prefix)) if text.startswith(prefix) else None
    )
    if match is None:
        raise UnsupportedCondition("unsupported complete knockout tournament condition")
    n = int(match["n"])
    if not byes and n & (n - 1):
        raise UnsupportedCondition(
            "a non-power-of-two tournament requires explicit random byes"
        )
    rounds = meeting_rounds(n)
    value = sum((p for _, p in rounds), Fraction(0))
    html = "<p>Способ 1. Разобьём встречу друзей по турам. Эти события несовместны. Пусть s — вероятность того, что оба дошли до текущего тура, ещё не встретившись. Изначально s=1.</p>"
    html += "<p>При чётном числе m участников вероятность встречи равна 1/(m−1); вероятность, что оба играют с другими и выигрывают, равна (m−2)/(4(m−1)). Для следующего тура умножаем s на эту величину.</p>"
    if byes:
        html += "<p>При нечётном m вероятность встречи равна 1/m. Вероятность, что оба останутся, не встретившись, складывается из двух случаев: оба играют с другими и выигрывают, либо один получает пропуск, а второй выигрывает:</p>"
        html += line(r"\frac{m-3}{m}\cdot\frac14+\frac2m\cdot\frac12=\frac{m+1}{4m}")
    html += "<p>Вероятности встречи по турам:</p>"
    for index, (players, probability) in enumerate(rounds, 1):
        html += line(rf"P_{{{index}}}={fmt(probability)}\quad(m={players})")
    html += line("P=" + "+".join(fmt(p) for _, p in rounds) + "=" + fmt(value))
    pairs = n * (n - 1) // 2
    games = [players // 2 for players, _ in rounds]
    html += "<p>Способ 2. По симметрии все пары исходных участников равноправны. В туре с m игроками проводится ⌊m/2⌋ встреч, поэтому вероятность встречи выбранной пары именно в этом туре равна числу игр, делённому на число всех пар:</p>"
    html += line(
        r"P=\frac{" + "+".join(str(g) for g in games) + rf"}}{{{pairs}}}={fmt(value)}"
    )
    html += "<p>Способ 3. Каждая игра исключает ровно одного участника, поэтому до единственного победителя состоится n−1 игр. Пара может встретиться не более одного раза. Все пары равноправны, следовательно:</p>"
    html += line(rf"P=\frac{{n-1}}{{\binom n2}}=\frac2n=\frac2{{{n}}}={fmt(value)}")
    answer, html = result(value, html)
    return finish(condition, answer_section, solution, answer, html)
