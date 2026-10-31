"""Use monotonicity to display exact comparisons with logarithmic endpoints."""

import sympy as sp

from ..probability.common import line
from ..word_problems.water_season_proof import inline
from .exam_exponential_proof import n
from .exam_input import endpoint_texts
from .exam_scalar import compare
from .logarithm_arithmetic import actual
from .logarithm_parser import LogarithmParser


def selection(a, rendered):
    lower, upper, _lc, _uc = a.bounds
    texts = endpoint_texts(a.interval)
    html = (
        "<p>Отберём корни на промежутке "
        + inline(a.interval)
        + ". Сравнения с логарифмическими границами выполним по монотонности показательной функции:</p>"
    )
    for text, bound in zip(texts, (lower, upper)):
        if bound.is_Rational and r"\log_" in text:
            html += line(text + "=" + n(bound))
    for r in a.roots:
        for text, bound in zip(texts, (lower, upper)):
            if bound.is_Rational:
                continue
            node = LogarithmParser(text).parse()
            if node.kind != "log":
                continue
            base, arg = (actual(child.value) for child in node.children)
            order = compare(r, bound) * (1 if base > 1 else -1)
            html += line(
                n(sp.simplify(base**r))
                + ("<" if order < 0 else ">" if order > 0 else "=")
                + n(arg)
            )
        left, right = compare(r, lower), compare(r, upper)
        lo = n(lower) if lower.is_Rational else texts[0]
        hi = n(upper) if upper.is_Rational else texts[1]
        if left < 0:
            formula = rendered[r] + "<" + lo
        elif right > 0:
            formula = hi + "<" + rendered[r]
        elif left == 0:
            formula = rendered[r] + "=" + lo
        elif right == 0:
            formula = rendered[r] + "=" + hi
        else:
            formula = lo + "<" + rendered[r] + "<" + hi
        html += line(formula)
        html += (
            "<p>Следовательно, этот корень "
            + ("принадлежит" if r in a.selected else "не принадлежит")
            + " заданному промежутку.</p>"
        )
    return html
