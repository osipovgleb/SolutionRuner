"""Reuse only reviewed x-axis charts for the union of rational inverse branches."""

import json
from pathlib import Path

from ..probability import solution_diagrams
from ..probability.common import UnsupportedCondition
from .logarithmic_inequality_substitution import LogarithmicSubstitution
from .mixed_substitution_proof import model
from .rational_inequality_figures import read_formula, signature

SOURCES = json.loads(
    (
        Path(__file__).parent
        / "assets/exponential-inequalities/mixed-substitution.json"
    ).read_text()
)
KEY = "rational_inverse_union"
ALT = "Метод интервалов для объединения двух ветвей обратной замены"


def row_signature(a):
    if isinstance(a, LogarithmicSubstitution) or any(
        len(b.conditions) != 1 for b in a.branches
    ):
        return None
    return {
        "variable": "x",
        "operation": "union",
        "rows": [signature(b.conditions[0].stage) for b in a.branches],
        "domain": str(a.domain),
        "branches": [str(b.solution) for b in a.branches],
    }


def source(a):
    reviewed = row_signature(a)
    matches = [
        key
        for key, entry in SOURCES["figures"].items()
        if reviewed is not None and all(entry.get(k) == v for k, v in reviewed.items())
    ]
    if len(matches) > 1:
        raise UnsupportedCondition("the inverse union chart must be unambiguous")
    return next(iter(matches), None)


def required_assets(context):
    a = model(read_formula(context)[1])
    source_id = source(a)
    assets = context["normalized_content"].get("assets", [])
    if source_id is None or any(asset.get("asset_id") == source_id for asset in assets):
        return ()
    return (
        {"source_asset_id": source_id, "section_id": "solution:1", "alt_text": ALT},
    )


def chart(context, a):
    source_id = source(a)
    assets = context["normalized_content"].get("assets", [])
    if source_id is None:
        if assets:
            raise UnsupportedCondition(
                "this substitution has no compatible reviewed source chart"
            )
        return "", (), ()
    if len(assets) != 1 or assets[0].get("asset_id") != source_id:
        raise UnsupportedCondition(
            "the exact reviewed union chart is required without duplicates"
        )
    asset = assets[0]
    shared = "shared_" + source_id.replace("-", "")[:16]
    if (
        asset.get("asset_key") not in ("image_1", shared)
        or asset.get(
            "kind", "ordinary_image" if asset.get("asset_key") == shared else None
        )
        != "ordinary_image"
        or asset.get(
            "url", "/assets/" + source_id if asset.get("asset_key") == shared else None
        )
        != "/assets/" + source_id
    ):
        raise UnsupportedCondition("the reviewed union image identity must stay fixed")
    html, key, changes = solution_diagrams.image(
        context["normalized_content"], KEY, ALT, source_id=source_id
    )
    return html, (key,), tuple(changes)
