"""Family-income percentage rule for source group 99568."""
from __future__ import annotations
import re
from typing import Any
from .common import UnsupportedCondition, finalize, require_content

RULE = "word-problem-99568-family-income-system"
_TIMES = {"вдвое": 2, "втрое": 3, "вчетверо": 4, "впятеро": 5}
_CONDITION = re.compile(
    r"Семья состоит из мужа, жены и их дочери студентки\. Если бы зарплата мужа увеличилась (?P<husband>в\w+), общий доход семьи вырос бы на (?P<rise>[1-9]\d*)%\. "
    r"Если бы стипендия дочери уменьшилась (?P<daughter>в\w+), общий доход семьи сократился бы на (?P<fall>[1-9]\d*)%\. "
    r"Сколько процентов от общего дохода семьи составляет зарплата жены\?"
)

def _times(word: str) -> int:
    try: return _TIMES[word]
    except KeyError as exc: raise UnsupportedCondition(f"unsupported multiplier: {word}") from exc

def build_context_repair_plan(context: dict[str, Any]):
    _, condition, answer_section, solution_section, text = require_content(context)
    m = _CONDITION.fullmatch(text)
    if m is None: raise UnsupportedCondition("condition does not match group 99568 template")
    k, q = _times(m["husband"]), _times(m["daughter"])
    rise, fall = int(m["rise"]), int(m["fall"])
    husband = rise // (k - 1)
    daughter_num = fall * q
    if rise % (k - 1) or daughter_num % (q - 1): raise UnsupportedCondition("income shares must be integral")
    daughter = daughter_num // (q - 1)
    wife = 100 - husband - daughter
    main = (
        '<section data-content-kind="solution" data-solution-title="Решение">'
        f'<p>Увеличение зарплаты мужа в {k} раз добавляет к доходу семьи <span data-inline-latex="{k-1}"></span> его зарплаты. Поэтому зарплата мужа составляет <span data-inline-latex="\\frac{{{rise}}}{{{k-1}}}={husband}\\%"></span> общего дохода.</p>'
        f'<p>При уменьшении стипендии дочери в {q} раз доход семьи уменьшается на <span data-inline-latex="\\frac{{{q-1}}}{{{q}}}"></span> её стипендии. Значит, стипендия дочери составляет <span data-inline-latex="\\frac{{{fall}\\cdot {q}}}{{{q-1}}}={daughter}\\%"></span> общего дохода.</p>'
        f'<p>Тогда зарплата жены составляет <span data-inline-latex="100\\%-{husband}\\%-{daughter}\\%={wife}\\%"></span>.</p></section>'
    )
    system = (
        '<section data-content-kind="solution" data-solution-title="Приведем другое решение.">'
        '<p>Пусть <span data-inline-latex="М"></span> — зарплата мужа, <span data-inline-latex="Ж"></span> — зарплата жены, <span data-inline-latex="Д"></span> — стипендия дочери в процентах от общего дохода. Составим систему по условию:</p>'
        '<center><p><span data-inline-latex="\\begin{cases}'
        f'М+Ж+Д=100\\\\{k}М+Ж+Д=100+{rise}\\\\М+Ж+\\frac{{Д}}{{{q}}}=100-{fall}'
        '\\end{cases}"></span>.</p></center>'
        '<p>Поочередно вычтем из первого уравнения два других. Получим новую систему:</p>'
        '<center><p><span data-inline-latex="\\begin{cases}'
        f'М+Ж+Д=100\\\\{k-1}М={rise}\\\\\\frac{{{q-1}}}{{{q}}}Д={fall}'
        '\\end{cases}"></span>.</p></center>'
        f'<p>Отсюда <span data-inline-latex="М={husband}"></span>, <span data-inline-latex="Д={daughter}"></span>. Тогда <span data-inline-latex="Ж=100-{husband}-{daughter}={wife}"></span>.</p></section>'
    )
    return finalize(condition, answer_section, solution_section, wife, main + system, rewrite_existing_solution=True)
