"""Reuse certified numerical charts or prepare source-style local replacements."""

import json
import re
from pathlib import Path

from bs4 import BeautifulSoup

from ..probability import solution_diagrams
from ..probability.common import UnsupportedCondition
from .rational_inequality import analyze
from .rational_inequality_algebraic_methods import presentation
from .rational_inequality_methods import prepare
from .rational_inequality_svg import render, render_single

DIRECTORY = Path(__file__).parent / "assets/rational-inequalities"
SOURCES = json.loads((DIRECTORY / "sources.json").read_text())
KEY = "rational_sign_chart"
ALT = "Метод интервалов и ограничения исходных знаменателей"


def read(context):
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
    return (content, condition, answer, solution), analyze(formula.removesuffix("."))


def signature(a):
    return {
        "points": list(map(str, a.points)),
        "poles": list(map(str, a.poles)),
        "signs": list(a.signs),
        "operator": a.sign_operator,
    }


def selection(context, a, *, required=False):
    double = required is True or required == "double"
    build = (
        (lambda model: render_single(model, layout=required))
        if required in ("single", "radical_single", "vieta")
        else lambda model: render(model, double=double)
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
        entry = SOURCES["figures"].get(asset.get("asset_id"))
        shared = (
            entry is not None
            and entry.get("shareable") is True
            and asset.get("asset_key")
            == "shared_" + asset["asset_id"].replace("-", "")[:16]
        )
        if (
            entry is None
            or (asset.get("asset_key") != "image_1" and not shared)
            or asset.get("kind", "ordinary_image" if shared else None)
            != "ordinary_image"
            or asset.get("url", "/assets/" + asset["asset_id"] if shared else None)
            != "/assets/" + asset["asset_id"]
        ):
            raise UnsupportedCondition(
                "the source chart identity is outside visual review"
            )
        if all(entry[key] == value for key, value in signature(a).items()):
            if generated:
                raise UnsupportedCondition(
                    "a compatible chart needs no generated duplicate"
                )
            return asset["asset_id"], None
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


def opposite_required_assets(context):
    _, a = read(context)
    a = presentation(a, "opposite_fractions")
    prepare(a, "opposite_fractions")
    source_id = SOURCES["parents"]["opposite_fractions"]["chart_asset_id"]
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


def image(context, a, generated, *, required=False):
    source_id, svg = selection(context, a, required=required)
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


GROUPS = (
    (
        "508440",
        "0d1fc6df-0af1-476a-97dc-288e21a9c5cd",
        1,
        "Рациональные неравенства",
        1,
        "9c619907-5d8d-437c-b7dd-004b50ba3536",
        "sum_fractions",
    ),
    (
        "508518",
        "0cc30461-8d0e-45e1-81f0-bbaa38fa4237",
        2,
        "Рациональные неравенства",
        1,
        "9c619907-5d8d-437c-b7dd-004b50ba3536",
        "cancelled_fraction",
    ),
    (
        "508524",
        "161b9b2b-6043-487b-8c9e-ae6524a655f0",
        3,
        "Рациональные неравенства",
        1,
        "9c619907-5d8d-437c-b7dd-004b50ba3536",
        "direct_fraction",
    ),
    (
        "511560",
        "f4cce06a-c452-48b5-9aa6-ae6b57a3b13d",
        4,
        "Рациональные неравенства",
        1,
        "9c619907-5d8d-437c-b7dd-004b50ba3536",
        "long_division",
    ),
)


GROUPS += (
    (
        "507491",
        "5e392131-445d-43e1-a18b-c42676e39a52",
        6,
        "Рациональные неравенства",
        1,
        "9c619907-5d8d-437c-b7dd-004b50ba3536",
        "factor_cancelled",
    ),
    (
        "508404",
        "4a9fdb96-480b-4a83-b71a-5728bcd9c7bf",
        10,
        "Рациональные неравенства",
        1,
        "9c619907-5d8d-437c-b7dd-004b50ba3536",
        "square_numerator",
    ),
)


GROUPS += (
    (
        "508299",
        "3f76356c-3084-4994-9b96-1721998721ea",
        7,
        "Рациональные неравенства",
        1,
        "9c619907-5d8d-437c-b7dd-004b50ba3536",
        "opposite_fractions",
    ),
    (
        "508442",
        "f8930a4b-7e30-4d25-8104-a30db6e423a0",
        19,
        "Рациональные неравенства",
        1,
        "9c619907-5d8d-437c-b7dd-004b50ba3536",
        "vieta_quadratic",
    ),
    (
        "556602",
        "602b11f6-a087-48cb-a594-c915fa758e13",
        38,
        "Рациональные неравенства",
        1,
        "9c619907-5d8d-437c-b7dd-004b50ba3536",
        "cancelled_quadratic_sum",
    ),
)
