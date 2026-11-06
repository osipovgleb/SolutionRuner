"""Reuse certified numerical charts or prepare source-style local replacements."""

import json
import re
from pathlib import Path

from bs4 import BeautifulSoup

from ..probability import solution_diagrams
from ..probability.common import UnsupportedCondition
from .rational_inequality import analyze
from .rational_inequality_algebraic_methods import presentation
from .rational_inequality_groups import GROUPS as CATALOG_GROUPS
from .rational_inequality_hatched_svg import render as render_hatched
from .rational_inequality_methods import prepare
from .rational_inequality_svg import DIVISION_LAYOUTS, render, render_single

DIRECTORY = Path(__file__).parent / "assets/rational-inequalities"
SOURCES = json.loads((DIRECTORY / "sources.json").read_text())
GROUPS = CATALOG_GROUPS
KEY = "rational_sign_chart"
ALT = "Метод интервалов и ограничения исходных знаменателей"


def read_formula(context):
    content, condition, answer, solution, text = solution_diagrams.read(context)
    spans = BeautifulSoup(condition["html"], "html.parser").find_all(
        "span", attrs={"data-inline-latex": True}
    )
    if len(spans) != 1:
        raise UnsupportedCondition("one explicit inequality formula is required")
    formula = spans[0]["data-inline-latex"]
    if not re.fullmatch(
        r"Решите неравенство(?::\s*|\s+)" + re.escape(formula) + r"\s*\.?", text
    ):
        raise UnsupportedCondition(
            "the entire rational inequality instruction must be recognized"
        )
    return (content, condition, answer, solution), formula.removesuffix(".")


def read(context):
    sections, formula = read_formula(context)
    return sections, analyze(formula)


def signature(a):
    return {
        "points": list(map(str, a.points)),
        "poles": list(map(str, a.poles)),
        "signs": list(a.signs),
        "operator": a.sign_operator,
    }


def reviewed_asset(asset, *, figures=None):
    figures = SOURCES["figures"] if figures is None else figures
    entry = figures.get(asset.get("asset_id"))
    shared = (
        entry is not None
        and entry.get("shareable") is True
        and asset.get("asset_key")
        == "shared_" + asset["asset_id"].replace("-", "")[:16]
    )
    if (
        entry is None
        or (asset.get("asset_key") != "image_1" and not shared)
        or asset.get("kind", "ordinary_image" if shared else None) != "ordinary_image"
        or asset.get("url", "/assets/" + asset["asset_id"] if shared else None)
        != "/assets/" + asset["asset_id"]
    ):
        raise UnsupportedCondition("the source chart identity is outside visual review")
    return entry


def selection(context, a, *, required=False, variable="x"):
    double = required is True or required == "double"
    build = (
        render_hatched
        if required == "hatched_square"
        else (
            (lambda model: render_single(model, layout=required, variable=variable))
            if required
            in (
                "single",
                "radical_single",
                "vieta",
                "polynomial_single",
                *DIVISION_LAYOUTS,
            )
            else lambda model: render(model, double=double)
        )
    )
    assets = context["normalized_content"].get("assets", [])
    originals = [asset for asset in assets if asset.get("asset_key") != KEY]
    generated = [asset for asset in assets if asset.get("asset_key") == KEY]
    if len(originals) > 1 or len(generated) > 1:
        raise UnsupportedCondition(
            "at most one source chart and one prepared chart are supported"
        )
    if originals:
        asset = originals[0]
        entry = reviewed_asset(asset)
        if entry.get("variable", "x") != variable:
            raise UnsupportedCondition("the source chart must use the solved variable")
        if all(entry[key] == value for key, value in signature(a).items()):
            if generated:
                raise UnsupportedCondition(
                    "a compatible chart needs no generated duplicate"
                )
            return asset["asset_id"], None
        if entry.get("reuse_only"):
            raise UnsupportedCondition(
                "this reviewed source layout supports exact reuse only"
            )
        return None, (render(a, double=True) if double or entry["double"] else build(a))
    if required or generated:
        return None, build(a)
    return None, None


def diagram_specs(context):
    _, a = read(context)
    _, svg = selection(context, a)
    return (solution_diagrams.spec(KEY, svg),) if svg is not None else ()


def cancelled_diagram_specs(context):
    _, a = read(context)
    prepare(a, "cancelled_fraction")
    _, svg = selection(context, a, required=True)
    return (solution_diagrams.spec(KEY, svg),) if svg is not None else ()


def factor_cancelled_diagram_specs(context):
    _, a = read(context)
    prepare(a, "factor_cancelled")
    _, svg = selection(context, a, required="single")
    return (solution_diagrams.spec(KEY, svg),) if svg is not None else ()


def compatible_required_assets(context, method):
    _, a = read(context)
    a = presentation(a, method)
    prepare(a, method)
    source_id = SOURCES["parents"][method]["chart_asset_id"]
    if any(
        asset.get("asset_id") == source_id
        for asset in context["normalized_content"].get("assets", [])
    ):
        return ()
    entry = SOURCES["figures"][source_id]
    if all(entry[key] == value for key, value in signature(a).items()):
        return (
            {"source_asset_id": source_id, "section_id": "solution:1", "alt_text": ALT},
        )
    return ()


def opposite_required_assets(context):
    return compatible_required_assets(context, "opposite_fractions")


def quadratic_required_assets(context):
    return compatible_required_assets(context, "quadratic_right")


def polynomial_diagram_specs(context, method):
    _, a = read(context)
    a = presentation(a, method)
    prepare(a, method)
    if method == "quadratic_right" and quadratic_required_assets(context):
        return ()
    _, svg = selection(
        context, a, required=SOURCES["parents"][method]["required_chart"]
    )
    return (solution_diagrams.spec(KEY, svg),) if svg is not None else ()


def quadratic_diagram_specs(context):
    return polynomial_diagram_specs(context, "quadratic_right")


def cubic_diagram_specs(context):
    return polynomial_diagram_specs(context, "cubic_cancel")


def denominators_diagram_specs(context):
    return polynomial_diagram_specs(context, "quadratic_denominators")


def square_zero_diagram_specs(context):
    return polynomial_diagram_specs(context, "square_zero")


def fraction_division_diagram_specs(context):
    return polynomial_diagram_specs(context, "fraction_division")


def degree_division_diagram_specs(context):
    return polynomial_diagram_specs(context, "degree_division")


def split_cancel_diagram_specs(context):
    return polynomial_diagram_specs(context, "split_cancel")


def quartic_diagram_specs(context):
    return polynomial_diagram_specs(context, "quartic_cancel")


def square_diagram_specs(context):
    return polynomial_diagram_specs(context, "common_square")


def algebraic_diagram_specs(context, method):
    _, a = read(context)
    a = presentation(a, method)
    prepare(a, method)
    if method == "opposite_fractions" and opposite_required_assets(context):
        return ()
    _, svg = selection(
        context, a, required=SOURCES["parents"][method]["required_chart"]
    )
    return (solution_diagrams.spec(KEY, svg),) if svg is not None else ()


def opposite_diagram_specs(context):
    return algebraic_diagram_specs(context, "opposite_fractions")


def vieta_diagram_specs(context):
    return algebraic_diagram_specs(context, "vieta_quadratic")


def image(context, a, generated, *, required=False, variable="x"):
    source_id, svg = selection(context, a, required=required, variable=variable)
    if source_id is None and svg is None:
        if generated:
            raise UnsupportedCondition(
                "an unrequested rational chart must not be injected"
            )
        return "", (), []
    if source_id is not None and generated:
        raise UnsupportedCondition("the compatible source chart must be reused exactly")
    markup, key, changes = solution_diagrams.image(
        context["normalized_content"],
        KEY,
        ALT,
        source_id=source_id,
        svg=svg,
        generated=generated,
    )
    return markup, (key,), changes
