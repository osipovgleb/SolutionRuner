"""Reuse reviewed interval intersections; omit only reviewed decorative child icons."""

import json
from pathlib import Path

from ..probability import solution_diagrams
from ..probability.common import UnsupportedCondition
from .logarithm_factor_inequality import analyze
from .rational_inequality_figures import read_formula, reviewed_asset, signature

SOURCES = json.loads(
    (
        Path(__file__).parent / "assets/logarithmic-inequalities/factor-comparison.json"
    ).read_text()
)
ALT = "Пересечение решения неравенства с исходной областью определения логарифмов"


def compatible(entry, a):
    return (
        entry["stage"] == signature(a.stage)
        and entry["domain"] == str(a.domain)
        and entry["intersection"] == str(a.solution)
    )


def required_assets(context):
    if context["normalized_content"].get("assets"):
        return ()
    a = analyze(read_formula(context)[1])
    matches = [uid for uid, entry in SOURCES["figures"].items() if compatible(entry, a)]
    return (
        ({"source_asset_id": matches[0], "section_id": "solution:1", "alt_text": ALT},)
        if matches
        else ()
    )


def chart(content, condition, a, method):
    assets = content.get("assets", [])
    if condition.get("asset_keys") or len({v.get("asset_id") for v in assets}) != len(
        assets
    ):
        raise UnsupportedCondition(
            "unreviewed condition or duplicate figures are not supported"
        )
    images = []
    for asset in assets:
        uid = asset.get("asset_id")
        if not isinstance(uid, str) or uid in condition["html"]:
            raise UnsupportedCondition(
                "the reviewed child-only asset must belong to the solution"
            )
        if uid in SOURCES["decorative_assets"] and method == "factor_base_square":
            entry = SOURCES["decorative_assets"][uid]
            if (
                asset.get("asset_key") != entry["asset_key"]
                or asset.get("kind") != "ordinary_image"
                or asset.get("url") != "/assets/" + uid
            ):
                raise UnsupportedCondition(
                    "the decorative source icon identity changed"
                )
            continue
        entry = reviewed_asset(asset, figures=SOURCES["figures"])
        if method != "factor_product" or not compatible(entry, a):
            raise UnsupportedCondition(
                "the exact plotted stage, domain and intersection must match"
            )
        images.append(asset)
    if len(images) > 1:
        raise UnsupportedCondition("only one compatible intersection chart is needed")
    if not images:
        return "", (), ()
    html, key, changes = solution_diagrams.image(
        content, "factor_log_intersection", ALT, source_id=images[0]["asset_id"]
    )
    return html, (key,), tuple(changes)
