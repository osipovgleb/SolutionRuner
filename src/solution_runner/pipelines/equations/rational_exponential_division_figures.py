"""Keep reviewed division figures and prepare a corrected t label or source-style axis."""

import gzip
import hashlib
import json
from pathlib import Path

from ..probability import solution_diagrams
from ..probability.common import UnsupportedCondition
from .rational_exponential_figures import row_signature
from .rational_exponential_holes_svg import render
from .rational_exponential_substitution import analyze
from .rational_inequality_figures import read_formula, reviewed_asset

DIRECTORY = Path(__file__).parent / "assets"
SOURCES = json.loads(
    (DIRECTORY / "exponential-inequalities/division-substitutions.json").read_text()
)
KEY = "rational_exponential_division_chart"
ALT = "Метод интервалов по переменной t с сохранением сокращённой исключённой точки"


def compatible(entry, a):
    expected = row_signature(a)
    expected.pop("display_scope")
    return all(entry.get(k) == v for k, v in expected.items())


def corrected(entry):
    path = DIRECTORY / "rational-inequalities" / entry["prepared_file"]
    svg = gzip.decompress(path.read_bytes()).decode()
    if hashlib.sha256(svg.encode()).hexdigest() != entry["prepared_sha256"]:
        raise UnsupportedCondition(
            "the corrected axis must match the reviewed SVG bytes"
        )
    return svg


def matching(a):
    matches = [
        (key, entry)
        for key, entry in SOURCES["figures"].items()
        if compatible(entry, a)
    ]
    if len(matches) > 1:
        raise UnsupportedCondition(
            "one source division figure must match unambiguously"
        )
    return matches[0] if matches else (None, None)


def required_assets(context):
    if any(
        asset.get("asset_key") != KEY
        for asset in context["normalized_content"].get("assets", [])
    ):
        return ()
    key, entry = matching(analyze(read_formula(context)[1]))
    if entry is None or entry["source_variable"] != "t":
        return ()
    return ({"source_asset_id": key, "section_id": "solution:1", "alt_text": ALT},)


def selection(context, a, required):
    assets = context["normalized_content"].get("assets", [])
    original = [asset for asset in assets if asset.get("asset_key") != KEY]
    generated = [asset for asset in assets if asset.get("asset_key") == KEY]
    if len(original) > 1 or len(generated) > 1:
        raise UnsupportedCondition(
            "one source division chart and one prepared chart are supported"
        )
    if original:
        entry = reviewed_asset(original[0], figures=SOURCES["figures"])
        if compatible(entry, a):
            if entry["source_variable"] == "t":
                if generated:
                    raise UnsupportedCondition(
                        "an exactly compatible division chart needs no duplicate"
                    )
                return original[0]["asset_id"], None
            return None, corrected(entry)
    if not required and not original and not generated:
        return None, None
    _, entry = matching(a)
    if entry is not None and entry.get("prepared_file"):
        return None, corrected(entry)
    return None, render(a.stage)


def diagram_specs(context, *, required):
    a = analyze(read_formula(context)[1])
    _, svg = selection(context, a, required)
    return (solution_diagrams.spec(KEY, svg),) if svg is not None else ()


def contained_diagram_specs(context):
    return diagram_specs(context, required=True)


def cubic_diagram_specs(context):
    return diagram_specs(context, required=False)


def chart(context, a, generated, *, required):
    source_id, svg = selection(context, a, required)
    if source_id is None and svg is None:
        if generated:
            raise UnsupportedCondition(
                "an unrequested division diagram must not be injected"
            )
        return "", (), ()
    if source_id is not None and generated:
        raise UnsupportedCondition(
            "reuse the compatible division source without replacement"
        )
    html, key, changes = solution_diagrams.image(
        context["normalized_content"],
        KEY,
        ALT,
        source_id=source_id,
        svg=svg,
        generated=generated,
    )
    return html, (key,), tuple(changes)
