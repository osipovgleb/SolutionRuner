"""Recognize every word and formula of the six reviewed graph models."""

import re
from dataclasses import dataclass

import sympy as sp

from ..core.errors import ContentPlanError
from .graph_questions import read
from .hyperbola import number

FORMULAS = {
    r"f(x)=b+\log_{(a)}x": "log_vertical",
    r"f(x)=\log_{(a)}(x+b)": "log_horizontal",
    r"f(x)=a^{x}+b": "exp_vertical",
    r"f(x)=a^{x+b}": "exp_horizontal",
    r"f(x)=a^{x}": "exp_plain",
    r"f(x)=\log_ax": "log_plain",
}


@dataclass(frozen=True)
class Question:
    model: str
    mode: str
    target: sp.Rational


def parse(context):
    forms, text = read(context)
    if not forms or forms[0] not in FORMULAS:
        raise ContentPlanError(
            "an explicit inspected exponential or logarithmic formula is required"
        )
    prefix = r"На рисунке изображен график функции(?: вида)? @0@\s*\.\s*Найдите "
    match = None
    if len(forms) == 2 and re.fullmatch(prefix + r"@1@\s*\.", text):
        match = re.fullmatch(r"f\((.+)\)", forms[1])
        mode = "value"
    elif len(forms) == 2 and re.fullmatch(
        prefix + r"значение x\s*,\s*при котором @1@\s*\.", text
    ):
        match = re.fullmatch(r"f\(x\)=(.+)", forms[1])
        mode = "argument"
    elif len(forms) == 1:
        match = re.fullmatch(prefix + r"значение f\s*\(([^()]+)\)\s*\.", text)
        mode = "value"
    if not match:
        raise ContentPlanError(
            "the entire exponential or logarithmic graph question must match"
        )
    return Question(FORMULAS[forms[0]], mode, sp.Rational(number(match[1])))
