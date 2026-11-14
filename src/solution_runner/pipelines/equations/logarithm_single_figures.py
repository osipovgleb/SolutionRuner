"""Reuse the exact parent intersection chart or prepare matching child SVGs."""

import json
from pathlib import Path

from ..probability import solution_diagrams
from ..probability.common import UnsupportedCondition
from .logarithm_single_rationalization import analyze
from .logarithm_single_svg import render
from .rational_inequality_figures import read_formula, signature

SOURCES = json.loads(
    (
        Path(__file__).parent / "assets/logarithmic-inequalities/single-log.json"
    ).read_text()
)
KEY = "logarithm_single_intersection"
ALT = "Рационализированное неравенство, область определения и их пересечение"


def compatible(entry, a):
    return (
        entry.get("stage") == signature(a.product)
        and entry.get("domain") == str(a.domain)
        and entry.get("intersection") == str(a.solution)
    )


def required_assets(context):
    if context["normalized_content"].get("assets"):
        return ()
    a = analyze(read_formula(context)[1])
    matches = [uid for uid, e in SOURCES["figures"].items() if compatible(e, a)]
    if len(matches) > 1:
        raise UnsupportedCondition("one compatible parent chart needs no duplicate")
    return tuple(
        {"source_asset_id": uid, "section_id": "solution:1", "alt_text": ALT}
        for uid in matches
    )


def selection(context, a):
    content, condition, *_ = read_formula(context)[0]
    if condition.get("asset_keys"):
        raise UnsupportedCondition("the reviewed chart belongs only to the solution")
    originals = [v for v in content.get("assets", []) if v.get("asset_key") != KEY]
    if len(originals) > 1:
        raise UnsupportedCondition(
            "only one reviewed source intersection chart is supported"
        )
    matches = []
    for asset in originals:
        uid = asset.get("asset_id")
        entry = SOURCES["figures"].get(uid)
        shared = (
            isinstance(uid, str)
            and asset.get("asset_key") == "shared_" + uid.replace("-", "")[:16]
        )
        if (
            entry is None
            or asset.get("asset_key")
            not in (entry["asset_key"], "shared_" + uid.replace("-", "")[:16])
            or asset.get("kind", "ordinary_image" if shared else None)
            != "ordinary_image"
            or asset.get("url", "/assets/" + uid if shared else None)
            != "/assets/" + uid
            or uid in condition["html"]
            or not compatible(entry, a)
        ):
            raise UnsupportedCondition(
                "the complete reviewed chart identity and plotted mathematics must match"
            )
        matches.append(uid)
    if matches:
        return matches[0], None
    return None, render(a)


def diagram_specs(context):
    a = analyze(read_formula(context)[1])
    _, svg = selection(context, a)
    return (solution_diagrams.spec(KEY, svg),) if svg is not None else ()


def chart(context, a, generated):
    uid, svg = selection(context, a)
    if uid is not None and any(v.get("asset_key") == KEY for v in generated):
        raise UnsupportedCondition("an exact source chart must not be duplicated")
    html, key, changes = solution_diagrams.image(
        context["normalized_content"],
        KEY,
        ALT,
        source_id=uid,
        svg=svg,
        generated=generated,
    )
    return html, (key,), tuple(changes)
