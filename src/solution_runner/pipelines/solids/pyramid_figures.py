"""Retain native pyramid roles and restore reviewed compatible method diagrams."""

from dataclasses import replace

from bs4 import BeautifulSoup

from ..core.errors import ContentPlanError
from ..probability.solution_diagrams import spec
from ..quadrilaterals.parallelogram.midpoint_figures import _attach
from ..quadrilaterals.quantity_content import read_content
from ..triangles.isosceles.planner import _section
from ..triangles.isosceles.side_altitude_figures import _identity, condition_changes
from .pyramid_named_svg import render
from .pyramid_reader import read
from .pyramid_sources import DATA, RULES, source_bytes

KEY = "pyramid_named_solution"
MIDPOINTS = {"triangle_lateral", "triangle_apothem", "triangle_side"}
CENTERS = {"center_volume", "center_height", "center_area"}


def signature(m):
    return m.kind + "|" + m.body


def scene(m):
    if m.kind in MIDPOINTS:
        return ["midpoint", m.names[0], "".join(sorted(m.names[1]))]
    if m.kind in CENTERS:
        return ["center", m.names[0]]
    return None


def selection(context, rule=None):
    content, assets, owners = read_content(context, {"image_1", "image_2", KEY})
    condition = _section(content, "condition")
    if condition is None:
        raise ContentPlanError("one complete pyramid condition is required")
    images = BeautifulSoup(condition["html"], "html.parser").find_all("img")
    if len(images) > 1:
        raise ContentPlanError("one pyramid condition drawing is supported")
    m = read(condition["html"], images[0].get("data-asset-id") if images else None)
    if rule is not None and m.kind not in RULES[rule]:
        raise ContentPlanError(
            "the pyramid question differs from its reviewed parent methods"
        )
    if scene(m) is not None and len(assets) > 1:
        raise ContentPlanError("one named pyramid diagram is supported")
    for key, a in assets.items():
        if key == KEY:
            if owners[key] != "solution" or scene(m) is None:
                raise ContentPlanError(
                    "the generated named pyramid drawing belongs to the solution"
                )
            continue
        f = DATA["figures"].get(a["asset_id"])
        if (
            not f
            or signature(m) not in f["signatures"]
            or [key, owners[key]] not in f["slots"]
        ):
            raise ContentPlanError(
                "the pyramid drawing has another body, method or role"
            )
        if f.get("scene") is not None and scene(m) != f["scene"]:
            raise ContentPlanError("the pyramid drawing has different named points")
        if any(str(m.q.get(k)) != v for k, v in f.get("values", {}).items()):
            raise ContentPlanError(
                "the numerical pyramid drawing differs from the givens"
            )
        source_bytes(a["asset_id"])
    return m, condition, assets, owners


def choice(m, assets):
    desired = scene(m)
    if desired is None:
        return None, None
    native = next((a["asset_id"] for k, a in assets.items() if k != KEY), None)
    compatible = [
        src
        for src, f in DATA["figures"].items()
        if f.get("scene") == desired and signature(m) in f["signatures"]
    ]
    if compatible:
        return (native if native in compatible else compatible[0]), None
    if desired == ["midpoint", "M", "AB"]:
        src = "f7eb48c5-f8d0-484d-948c-78f5069e1968"
        return src, spec(
            KEY, render(src, "Q", "77bf12c5-015e-4b0f-a2c9-e9fdd7cb0f3f", "M")
        )
    if desired == ["center", "N"]:
        src = "ecbfb007-8435-4873-aa42-8d483008bc19"
        return src, spec(
            KEY, render(src, "O", "d4a1ebbe-e356-4338-8c77-ad60612eda6c", "N")
        )
    raise ContentPlanError("this named pyramid scene needs review")


def diagram_specs(context):
    m, _condition, assets, _owners = selection(context)
    drawing = choice(m, assets)[1]
    return (drawing,) if drawing else ()


def _slots(m, assets, owners):
    slots = {key: (owners[key], a["asset_id"]) for key, a in assets.items()}
    roles = set(owners.values())
    for key, (role, source) in DATA["defaults"][signature(m)].items():
        if role in roles or role == "condition" and "solution" in roles:
            continue
        if key in slots:
            raise ContentPlanError(
                "restoring this pyramid figure needs a reviewed slot"
            )
        slots[key] = (role, source)
        roles.add(role)
    return slots


def prepare(context, generated, rule):
    m, condition, assets, owners = selection(context, rule)
    changes = []
    pictures = {}
    keys = []
    if scene(m) is not None:
        source, drawing = choice(m, assets)
        old = next(iter(assets.values()), None)
        key = KEY if drawing else old["asset_key"] if old else "image_1"
        identifier, url = _identity(key, source, drawing, generated)
        picture, attached = _attach(old, key, identifier, url, "solution")
        return m, tuple(attached), {key: picture}, (key,)
    if generated:
        raise ContentPlanError("this pyramid needs no generated diagram")
    for key, (role, source) in _slots(m, assets, owners).items():
        current = assets.get(key, {})
        if role == "condition":
            changes.extend(
                condition_changes(
                    context,
                    condition,
                    current,
                    key,
                    source,
                    "/assets/" + source,
                    preserve_assets=("image_1", "image_2"),
                )
            )
        else:
            picture, attached = _attach(
                current or None, key, source, "/assets/" + source, "solution"
            )
            changes.extend(attached)
            pictures[key] = picture
            keys.append(key)
            if DATA["figures"][source].get("symbols"):
                m = replace(m, symbols=DATA["figures"][source]["symbols"])
    return m, tuple(changes), pictures, tuple(keys)
