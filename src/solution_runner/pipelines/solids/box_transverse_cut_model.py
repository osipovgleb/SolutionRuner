"""One transverse box plane with two question forms and two reference faces."""

import re

import sympy as sp

from ..core.errors import ContentPlanError
from ..word_problems.common import UnsupportedCondition
from .measurements import positive
from .spatial_metric_model import model

MODES = {"box_transverse_ratio_angle", "box_transverse_incidence_angle"}
RATIO = r"\s*(?:\\colon|:)\s*"
START = (
    r"На ребре AA_1 прямоугольного параллелепипеда ABCDA_1B_1C_1D_1 взята точка E так, что A_1E"
    + RATIO
    + r"EA\s*=\s*(.+?)"
    + RATIO
    + r"(.+?)"
)
MIDPOINT = r"Точка T — середина ребра B_1C_1\. "
DIMENSIONS = r"Известно, что AB\s*=\s*(.+?), AD\s*=\s*(.+?), AA_1\s*=\s*(.+?)\. "
DIRECT = (
    r"\. "
    + MIDPOINT
    + DIMENSIONS
    + r"[ВB] каком отношении плоскость ETD_1 делит ребро BB_1\s*\? Найдите угол между плоскостью ETD_1 и плоскостью AA_1B_1\."
)
INCIDENCE = (
    r", на ребре BB_1 — точка F так, что B_1F"
    + RATIO
    + r"FB\s*=\s*(.+?)"
    + RATIO
    + r"(.+?), "
    r"а точка T — середина ребра B_1C_1\. "
    + DIMENSIONS
    + r"Докажите, что плоскость EFT проходит через вершину D_1\. Найдите угол между плоскостью EFT и плоскостью BB_1C_1\."
)


def _build(tokens, incidence):
    if incidence:
        p, q, fp, fq, a, b, h = map(positive, tokens)
    else:
        p, q, a, b, h = map(positive, tokens)
    d = h * p / (p + q)
    top = d / 2
    if incidence and sp.simplify(h * fp / (fp + fq) - top) != 0:
        raise ContentPlanError(
            "the given edge ratios do not put D1 in the transverse plane"
        )
    eq = sp.sqrt(a * a + top * top)
    ft = sp.sqrt(b * b + d * d) / 2
    altitude = b * d / (4 * ft)
    tan = a / altitude if incidence else b * eq / (a * d)
    values = {
        "a": a,
        "b": b,
        "height": h,
        "p": p,
        "q": q,
        "d": d,
        "AE": h - d,
        "B1F": top,
        "FB": h - top,
        "B1T": b / 2,
        "ratio": top / (h - top),
        "EQ": eq,
        "A1H": a * d / eq,
        "foot": d * d / (2 * eq * eq),
        "FT": ft,
        "B1K": altitude,
        "tan": tan,
        "cos": 1 / sp.sqrt(1 + tan * tan),
    }
    if incidence:
        values.update(fp=fp, fq=fq)
    return model(
        "box_transverse_" + ("incidence_angle" if incidence else "ratio_angle"),
        tuple(
            (k, values[k])
            for k in ("a", "b", "height", "p", "q")
            + (("fp", "fq") if incidence else ())
        ),
        values,
        ("F" if incidence else "Q",),
        sp.acos(values["cos"]) if incidence else sp.atan(tan),
    )


def read(raw):
    for ending, incidence in ((DIRECT, False), (INCIDENCE, True)):
        match = re.fullmatch(START + ending, raw)
        if match:
            try:
                return _build(match.groups(), incidence)
            except UnsupportedCondition as exc:
                raise ContentPlanError(
                    "complete positive transverse-plane measurements are required"
                ) from exc
    return None
