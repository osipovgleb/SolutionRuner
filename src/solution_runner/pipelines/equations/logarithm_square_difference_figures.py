"""Reuse both exact parent figures or prepare both child sign-system charts."""

import json
from pathlib import Path

import sympy as sp

from ..probability import solution_diagrams
from ..probability.common import UnsupportedCondition
from .logarithm_square_difference import analyze
from .logarithm_square_difference_svg import render
from .rational_inequality_figures import read_formula, signature

SOURCES = json.loads(
    (
        Path(__file__).parent / "assets/logarithmic-inequalities/square-difference.json"
    ).read_text()
)
ALT = "Область определения и пересечение двух условий знака"
KEYS = ("logarithm_square_system_1", "logarithm_square_system_2")


def compatible(entry, a, index):
    branch = a.systems[index]
    domain = a.coarse_domain if entry["omit_domain_hole"] else a.domain
    if (
        entry["omit_domain_hole"]
        and sp.Intersection(
            a.coarse_domain, branch.sum_stage.solution, branch.difference_stage.solution
        )
        != sp.EmptySet
    ):
        return False
    return (
        entry["branch"] == index
        and entry["domain"] == str(domain)
        and entry["hole"] == str(a.hole)
        and entry["difference"] == signature(branch.difference_stage)
        and entry["sum"] == signature(branch.sum_stage)
        and entry["intersection"] == str(branch.solution)
    )


def required_assets(context):
    if context["normalized_content"].get("assets"):
        return ()
    a = analyze(read_formula(context)[1])
    return tuple(
        {"source_asset_id": uid, "section_id": "solution:1", "alt_text": ALT}
        for uid, entry in SOURCES["figures"].items()
        if compatible(entry, a, entry["branch"])
    )


def selection(
    context,
    a,
    index,
    *,
    figures=None,
    keys=KEYS,
    compatible_fn=compatible,
    renderer=render,
):
    figures = SOURCES["figures"] if figures is None else figures
    content, condition, *_ = read_formula(context)[0]
    if condition.get("asset_keys"):
        raise UnsupportedCondition("the reviewed figures belong only to the solution")
    originals = [
        asset
        for asset in content.get("assets", [])
        if asset.get("asset_key") not in keys
    ]
    if len(originals) > 2 or len({asset.get("asset_id") for asset in originals}) != len(
        originals
    ):
        raise UnsupportedCondition(
            "only the two distinct reviewed source diagrams are supported"
        )
    matches = []
    for asset in originals:
        uid = asset.get("asset_id")
        entry = figures.get(uid)
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
        ):
            raise UnsupportedCondition(
                "the complete reviewed source figure identity is required"
            )
        if not compatible_fn(entry, a, entry["branch"]):
            raise UnsupportedCondition(
                "all displayed rows and the final intersection must match the source"
            )
        if entry["branch"] == index:
            matches.append(uid)
    if len(matches) > 1:
        raise UnsupportedCondition("a compatible chart needs no duplicate")
    return (matches[0], None) if matches else (None, renderer(a, index))


def diagram_specs(context):
    a = analyze(read_formula(context)[1])
    specs = []
    for index, key in enumerate(KEYS):
        _, svg = selection(context, a, index)
        if svg is not None:
            specs.append(solution_diagrams.spec(key, svg))
    return tuple(specs)


def charts(context, a, generated, *, chart_keys=KEYS, selector=selection, alt=ALT):
    html = []
    keys = []
    changes = []
    for index, key in enumerate(chart_keys):
        uid, svg = selector(context, a, index)
        if uid is not None and any(v.get("asset_key") == key for v in generated):
            raise UnsupportedCondition("an exact source chart must not be duplicated")
        markup, asset_key, updates = solution_diagrams.image(
            context["normalized_content"],
            key,
            alt,
            source_id=uid,
            svg=svg,
            generated=generated,
        )
        html.append(markup)
        keys.append(asset_key)
        changes.extend(updates)
    return tuple(html), tuple(keys), tuple(changes)
