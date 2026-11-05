"""Preserve reviewed native roles and correct the one incompatible nested-cone source."""

import hashlib

from bs4 import BeautifulSoup

from ..core.errors import ContentPlanError
from ..quadrilaterals.parallelogram.midpoint_figures import _attach
from ..quadrilaterals.quantity_content import read_content
from ..triangles.isosceles.planner import _section
from ..triangles.isosceles.side_altitude_figures import condition_changes
from .combined_content import unique_diagram
from .combined_reader import read
from .combined_sources import DATA, RULES, source_bytes


def selection(context, rule):
    content, assets, owners = read_content(unique_diagram(context), {"image_1"})
    condition = _section(content, "condition")
    if condition is None:
        raise ContentPlanError("one complete solid-combination condition is required")
    images = BeautifulSoup(condition["html"], "html.parser").find_all("img")
    if len(images) > 1 or len(assets) > 1:
        raise ContentPlanError("one solid-combination diagram is supported")
    m = read(condition["html"], images[0].get("data-asset-id") if images else None)
    if m.kind not in RULES[rule]:
        raise ContentPlanError(
            "the combination differs from the reviewed parent method"
        )
    if m.kind == "cube_prism_hole" and not assets:
        review = DATA["restorations"].get(context.get("problem_id"))
        if (
            not review
            or review["condition_sha256"]
            != hashlib.sha256(condition["html"].encode()).hexdigest()
        ):
            raise ContentPlanError(
                "the missing through-hole diagram needs an explicit source review"
            )
    scene = DATA["scenes"].get(m.kind, m.kind)
    for key, a in assets.items():
        f = DATA["figures"].get(a["asset_id"])
        if not f or f["scene"] != scene or [key, owners[key]] not in f["slots"]:
            raise ContentPlanError(
                "the combination diagram has another inscription or role"
            )
        source_bytes(a["asset_id"])
    return m, condition, assets, owners


def prepare(context, generated, rule):
    if generated:
        raise ContentPlanError("these solid combinations reuse exact source diagrams")
    m, condition, assets, owners = selection(context, rule)
    if assets:
        slots = {key: (owners[key], a["asset_id"]) for key, a in assets.items()}
    elif m.kind == "cube_prism_hole":
        review = DATA["restorations"][context["problem_id"]]
        slots = {"image_1": (review["role"], review["source"])}
    else:
        slots = DATA["defaults"][m.kind]
    changes, pictures, keys = [], {}, []
    for key, (role, source) in slots.items():
        source = DATA["corrections"].get(source, source)
        source_bytes(source)
        current = assets.get(key, {})
        if role == "condition":
            changes.extend(
                condition_changes(
                    context, condition, current, key, source, "/assets/" + source
                )
            )
        else:
            picture, attached = _attach(
                current or None, key, source, "/assets/" + source, "solution"
            )
            changes.extend(attached)
            pictures[key] = picture
            keys.append(key)
    return m, tuple(changes), pictures, tuple(keys)
