"""Equal rise-and-fall percent rule for source group 99566."""

from __future__ import annotations

from math import isqrt
import re
from typing import Any

from .common import UnsupportedCondition, finalize, require_content


RULE = "word-problem-99566-equal-rise-fall-percent"
_CONDITION = re.compile(
    r"В (?P<first_day>понедельник|среду|четверг) акции компании подорожали на некоторое (?:количество|число) процентов, "
    r"а (?:во вторник|в четверг|в пятницу) подешевели на то же самое (?:количество|число) процентов\. "
    r"В результате они стали стоить на (?P<loss>[1-9]\d*)% дешевле, чем при открытии торгов в "
    r"(?P=first_day)\. На сколько процентов подорожали акции компании в (?P=first_day)\?"
)


def build_context_repair_plan(context: dict[str, Any]):
    _, condition, answer_section, solution_section, text = require_content(context, allow_inline_latex=True)
    match = _CONDITION.fullmatch(text)
    if match is None:
        raise UnsupportedCondition("condition does not match group 99566 template")

    loss = int(match["loss"])
    root = isqrt(loss)
    if root * root != loss:
        raise UnsupportedCondition("the loss percentage must be a perfect square")
    answer = 10 * root
    solution_html = (
        '<section data-content-kind="solution" data-solution-title="Решение">'
        '<p>При увеличении первоначальной стоимости <span data-inline-latex="S"></span> на '
        '<span data-inline-latex="x\\%"></span> она становится равной '
        '<span data-inline-latex="S\\left(1+\\frac{x}{100}\\right)"></span>. После уменьшения на столько же процентов стоимость равна '
        '<span data-inline-latex="S\\left(1+\\frac{x}{100}\\right)\\left(1-\\frac{x}{100}\\right)"></span>.</p>'
        f'<p>По условию итоговая стоимость на <span data-inline-latex="{loss}\\%"></span> меньше первоначальной:</p>'
        '<center><p><span data-inline-latex="'
        f'S\\left(1+\\frac{{x}}{{100}}\\right)\\left(1-\\frac{{x}}{{100}}\\right)=S\\left(1-\\frac{{{loss}}}{{100}}\\right)'
        '"></span>.</p></center>'
        '<p>Так как <span data-inline-latex="S\\ne0"></span>, сократим обе части равенства на <span data-inline-latex="S"></span> и решим уравнение:</p>'
        '<center><p><span data-inline-latex="'
        f'1-\\frac{{x^2}}{{10000}}=1-\\frac{{{loss}}}{{100}}\\iff \\frac{{x^2}}{{10000}}=\\frac{{{loss}}}{{100}}\\iff x^2={100 * loss}\\iff x={answer}'
        '"></span>.</p></center>'
        '</section>'
        '<section data-content-kind="solution" data-solution-title="ЛАЙФХАК">'
        '<p>Во всех задачах этого вида решение получается одинаковым:</p>'
        '<ul><li>берём единственное число <span data-inline-latex="r"></span> из условия — процент итогового удешевления;</li>'
        '<li>считаем <span data-inline-latex="\\sqrt{r}\\cdot10"></span>.</li></ul>'
        f'<p>Здесь <span data-inline-latex="\\sqrt{{{loss}}}\\cdot10={root}\\cdot10={answer}"></span>.</p>'
        '</section>'
    )
    return finalize(
        condition, answer_section, solution_section, answer, solution_html,
        rewrite_existing_solution=True,
    )
