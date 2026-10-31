"""Read only the prototype's substitution style, never its numeric answers."""

import re

from bs4 import BeautifulSoup

from ..word_problems.common import UnsupportedCondition
from .power_arithmetic import balanced, clean

POWER = r"(?:\d+|\(\\frac\{\d+\}\{\d+\}\))\^"
RATIO = r"\(\\frac\{\d+\}\{\d+\}\)\^"


def style(parent_html):
    from .exam_exponential import X, polynomial

    explicit = []
    implicit = []
    for span in BeautifulSoup(parent_html, "html.parser").select(
        "span[data-inline-latex]"
    ):
        raw = span["data-inline-latex"]
        probe = "".join(raw.split())
        if probe.startswith("t=") or probe.endswith("=t"):
            text = clean(raw)
            text = text[2:] if text.startswith("t=") else text[:-2]
            m = re.match(POWER, text)
            if m:
                exponent, end = balanced(text, m.end())
                if end == len(text):
                    explicit.append(polynomial(exponent).subs(X, 0) != 0)
        for m in re.finditer(RATIO, probe):
            exponent, _ = balanced(probe, m.end())
            implicit.append(polynomial(exponent).subs(X, 0) != 0)
    choices = explicit or implicit
    if not choices or len(set(choices)) != 1:
        raise UnsupportedCondition(
            "the parent must specify one consistent exponential substitution"
        )
    return choices[0], bool(explicit)
