"""Read the whole hyperbola condition, preserving the audited image identity."""

import re

from ..core.errors import ContentPlanError
from .graph_questions import read

_INTRO = r"На рисунке изображен график функции(?: вида)? @0@"
_PREFIX = _INTRO + r"\s*\.\s*"
_NUMERIC = r"-?\d+(?:[,.]\d+)?"


def shifted(context, mode, horizontal_model):
    forms, text = read(context)
    if not forms or forms[0] not in {r"f(x)=\frac{k}{x}+a", r"f(x)=\frac{k}{x+a}"}:
        raise ContentPlanError("condition is not a supported shifted hyperbola")
    horizontal = horizontal_model or forms[0] == r"f(x)=\frac{k}{x+a}"
    if mode == "value":
        target = re.fullmatch(r"f\((.+)\)", forms[1]) if len(forms) == 2 else None
        if not target or not re.fullmatch(_PREFIX + r"Найдите @1@\s*\.", text):
            raise ContentPlanError("unsupported complete function-value question")
        return horizontal, target[1]
    if mode != "argument":
        raise ContentPlanError("unknown hyperbola question mode")
    if horizontal:
        target = re.fullmatch(r"f\(x\)=(.+)", forms[-1])
        variable = "@1@" if len(forms) == 3 and forms[1] == "x" else "x"
        pattern = (
            _PREFIX
            + r"Найдите значение "
            + variable
            + r"\s*,\s*при котором @"
            + str(len(forms) - 1)
            + r"@\s*\."
        )
        if (
            len(forms) not in (2, 3)
            or (len(forms) == 3 and forms[1] != "x")
            or not target
            or not re.fullmatch(pattern, text)
        ):
            raise ContentPlanError(
                "unsupported complete horizontal inverse-function question"
            )
    else:
        target = re.fullmatch(
            _PREFIX
            + r"Найдите, при каком значении x значение функции равно ("
            + _NUMERIC
            + r")\s*\.",
            text,
        )
        if len(forms) != 1 or not target:
            raise ContentPlanError("unsupported complete inverse-function question")
    return horizontal, target[1]


def fractional(context):
    forms, text = read(context)
    models = (
        r"f(x)=\frac{k}{x}+ax+b",
        r"f(x)=\frac{kx+a}{x+b}",
        r"f(x)=\frac{ax+b}{x+c}",
    )
    asked = forms[1] if len(forms) == 2 else None
    whole = bool(forms and forms[0] == models[2] and "где числа" in text)
    prefix = (
        _INTRO + r"\s*,\s*где числа a\s*,\s*b и c — целые\.\s*" if whole else _PREFIX
    )
    pattern = (
        prefix
        + r"Найдите (?:коэффициент )?"
        + (r"@1@" if asked else r"([kabc])")
        + r"\s*\."
    )
    match = re.fullmatch(pattern, text)
    if not forms or forms[0] not in models or len(forms) not in (1, 2) or not match:
        raise ContentPlanError("unsupported complete fractional hyperbola question")
    asked = asked or match[1]
    abc = forms[0] == models[2]
    sought = {"a": "k", "b": "a", "c": "b"}.get(asked) if abc else asked
    if sought not in {"k", "a", "b"}:
        raise ContentPlanError("unsupported fractional hyperbola coefficient")
    return abc, sought, whole


def unshifted(context):
    forms, text = read(context)
    if not forms or forms[0] != r"f(x)=\frac{k}{x}":
        raise ContentPlanError("unsupported unshifted hyperbola question")
    if len(forms) == 2 and re.fullmatch(_PREFIX + r"Найдите @1@\s*\.", text):
        match = re.fullmatch(r"f\((.+)\)", forms[1])
    else:
        match = (
            re.fullmatch(
                _PREFIX + r"Найдите f\s*\(\s*(" + _NUMERIC + r")\s*\)\s*\.", text
            )
            if len(forms) == 1
            else None
        )
    if not match:
        raise ContentPlanError("unsupported complete unshifted hyperbola question")
    return match[1]
