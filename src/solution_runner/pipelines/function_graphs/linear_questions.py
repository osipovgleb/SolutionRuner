"""Values, inverse values and the requested coordinate of two intersecting lines."""

import re

from ..core.errors import ContentPlanError
from .graph_questions import read
from .hyperbola import number

_PREFIX = r"На рисунке изображен график функции @0@\s*\.\s*"


def parse(context):
    forms, text = read(context)
    if not forms:
        match = re.fullmatch(
            r"На рисунке изображены графики двух линейных функций\. Найдите (абсциссу|ординату) точки пересечения графиков\.",
            text,
        )
        if match:
            return "intersection_x" if match[
                1
            ] == "абсциссу" else "intersection_y", None
    if forms and forms[0] == "f(x)=kx+b":
        if len(forms) == 2 and re.fullmatch(_PREFIX + r"Найдите @1@\s*\.", text):
            match = re.fullmatch(r"f\((.+)\)", forms[1])
            if match:
                return "value", number(match[1])
        variable = "@1@" if len(forms) == 3 and forms[1] == "x" else "x"
        pattern = (
            _PREFIX
            + "Найдите значение "
            + variable
            + r"\s*,\s*при котором @"
            + str(len(forms) - 1)
            + r"@\s*\."
        )
        if len(forms) in (2, 3) and re.fullmatch(pattern, text):
            match = re.fullmatch(r"f\(x\)=(.+)", forms[-1])
            if match:
                return "argument", number(match[1])
    raise ContentPlanError(
        "the complete linear-function graph question must be recognized"
    )
