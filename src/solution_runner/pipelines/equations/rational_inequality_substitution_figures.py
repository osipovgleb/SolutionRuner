"""Certify z-axis charts and exact two-row reciprocal-sum intersection diagrams."""

from ..probability import solution_diagrams
from ..probability.common import UnsupportedCondition
from .rational_inequality_figures import (
    ALT,
    KEY,
    SOURCES,
    image,
    read,
    reviewed_asset,
    selection,
    signature,
)
from .rational_inequality_substitutions import model


def row_signature(m):
    return {"variable": m.variable, "rows": [signature(a) for a in m.rows]}


def reciprocal_source(m):
    source_id = SOURCES["parents"]["reciprocal_square"]["chart_asset_id"]
    entry = SOURCES["figures"][source_id]
    if any(entry.get(key) != value for key, value in row_signature(m).items()):
        raise UnsupportedCondition(
            "the two solved inequalities must match the reviewed intersection chart"
        )
    return source_id


def reciprocal_required_assets(context):
    m = model(read(context)[1], "reciprocal_square")
    source_id = reciprocal_source(m)
    if any(
        asset.get("asset_id") == source_id
        for asset in context["normalized_content"].get("assets", [])
    ):
        return ()
    return (
        {"source_asset_id": source_id, "section_id": "solution:1", "alt_text": ALT},
    )


def diagram_specs(context, method):
    m = model(read(context)[1], method)
    if method == "reciprocal_square":
        reciprocal_source(m)
        return ()
    _, svg = selection(context, m.stage, required="single", variable=m.variable)
    return (solution_diagrams.spec(KEY, svg),) if svg is not None else ()


def affine_diagram_specs(context):
    return diagram_specs(context, "affine_radical")


def reciprocal_diagram_specs(context):
    return diagram_specs(context, "reciprocal_square")


def chart(context, m, generated):
    if not m.rows:
        return image(
            context, m.stage, generated, required="single", variable=m.variable
        )
    source_id = reciprocal_source(m)
    assets = context["normalized_content"].get("assets", [])
    if generated or len(assets) != 1 or assets[0].get("asset_id") != source_id:
        raise UnsupportedCondition(
            "the exact compatible intersection chart is required without duplicates"
        )
    reviewed_asset(assets[0])
    markup, key, changes = solution_diagrams.image(
        context["normalized_content"], KEY, ALT, source_id=source_id
    )
    return markup, (key,), changes
