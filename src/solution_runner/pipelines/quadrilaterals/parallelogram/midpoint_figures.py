"""Reuse exact compatible midpoint images; relabel the reviewed style otherwise."""

from types import SimpleNamespace

from bs4 import BeautifulSoup

from ...core.errors import ContentPlanError
from ...probability.solution_diagrams import spec
from ...triangles.general.simple_angle_figures import _remapped
from ...triangles.isosceles.planner import _section
from ...triangles.isosceles.side_altitude_figures import _identity
from ...triangles.right.basic_parent import _targeted
from ...word_problems.common import rewrite
from .midpoint_assets import PREFIX, read_assets, seed
from .midpoint_model import read_question
from .midpoint_sources import (
    HEIGHT_CONDITION,
    SOURCES,
    TRAPEZOID_HEIGHT,
    TRAPEZOID_MEDIAN,
    TRIANGLE_HEIGHT,
    VARIGNON_FIGURE,
    source_bytes,
)


def _diagram(model, source, key):
    _, old_frame, _, names = SOURCES[source]
    if model.frame == old_frame:
        return None
    inverse = str.maketrans(old_frame, "ABCD")
    transform = SimpleNamespace(name=lambda label: model.name(label.translate(inverse)))
    return spec(key, _remapped(transform, source_bytes(source), names))


def selection(context):
    content = context.get("normalized_content")
    if (
        not isinstance(content, dict)
        or content.get("schema_version") != 3
        or content.get("format") != "teacherhelper-normalized"
    ):
        raise ContentPlanError("schema-v3 normalized midpoint content is required")
    assets, owners = read_assets(content)
    condition = _section(content, "condition")
    if condition is None:
        raise ContentPlanError("one midpoint condition is required")
    soup = BeautifulSoup(condition["html"], "html.parser")
    images = soup.find_all("img")
    if len(images) > 1:
        raise ContentPlanError("at most one midpoint condition figure is supported")
    source = images[0]["data-asset-id"] if images else None
    if images:
        images[0]["data-asset-key"] = "image_1"
    model = read_question(str(soup), source)
    if any(SOURCES[seed(a)][0] != model.mode for a in assets.values()):
        raise ContentPlanError(
            "the midpoint diagrams depict another mathematical object"
        )
    height_only = any(seed(a) == HEIGHT_CONDITION for a in assets.values())
    figures = _select_figures(model, height_only, assets, owners)
    return model, height_only, condition, assets, figures


def _select_figures(model, height_only, assets, owners):
    roles = {
        "trapezoid": (HEIGHT_CONDITION,)
        if height_only
        else (TRAPEZOID_HEIGHT, TRAPEZOID_MEDIAN),
        "triangle": tuple(
            seed(assets[k]) for k, owner in owners.items() if owner == "condition"
        )
        + (TRIANGLE_HEIGHT,),
        "varignon": (VARIGNON_FIGURE,),
    }[model.mode]
    figures, used = [], set()
    for preferred in roles:
        part = SOURCES[preferred][2]
        current = [a for a in assets.values() if SOURCES[seed(a)][2] == part]
        if len(current) > 1:
            raise ContentPlanError("duplicate figures for one midpoint method")
        old = current[0] if current else None
        source = seed(old) if old else preferred
        if SOURCES[source][1] != model.frame:
            source = next(
                (
                    s
                    for s, (mode, frame, role, _) in SOURCES.items()
                    if (mode, frame, role) == (model.mode, model.frame, part)
                ),
                source,
            )
        generated_key = PREFIX + source
        diagram = _diagram(model, source, generated_key)
        key = (
            generated_key
            if diagram
            else old["asset_key"]
            if old and not old["asset_key"].startswith(PREFIX)
            else next(
                k
                for k in ("image_1", "image_2")
                if k not in used and (k not in assets or assets[k] is old)
            )
        )
        used.add(key)
        figures.append((part, old, source, key, diagram))
    if {f[1]["asset_key"] for f in figures if f[1]} != set(assets):
        raise ContentPlanError("a midpoint figure has no reviewed method")
    return figures


def diagram_specs(context):
    return tuple(f[-1] for f in selection(context)[-1] if f[-1] is not None)


def _attach(old, key, identifier, url, owner):
    image = BeautifulSoup('<img alt=""/>', "html.parser").img
    image.attrs.update(
        {
            "data-asset-key": key,
            "data-asset-id": identifier,
            "src": url,
            "data-transformation-target-id": "asset:" + key,
        }
    )
    changes = []
    if old is None or (old["asset_key"], old["asset_id"]) != (key, identifier):
        changes.append(
            {
                "transformation_target_id": "asset:" + key,
                "operation": "rewrite" if old and old["asset_key"] == key else "add",
                "value": {
                    "asset_key": key,
                    "asset_id": identifier,
                    "url": url,
                    "kind": "ordinary_image",
                    "alt": "",
                    "position": 0,
                    "parent_target_id": "section:" + owner + ":1",
                    "html": str(image),
                },
            }
        )
        if old and old["asset_key"] != key:
            changes.append(
                {
                    "transformation_target_id": "asset:" + old["asset_key"],
                    "operation": "remove",
                }
            )
    return str(image), changes


def prepare(context, generated):
    model, height_only, condition, _assets, figures = selection(context)
    expected = {f[-1]["asset_key"] for f in figures if f[-1]}
    if (
        len(generated) != len(expected)
        or {g.get("asset_key") for g in generated} != expected
    ):
        raise ContentPlanError("the prepared midpoint figures differ from the methods")
    changes, pictures, keys = [], {}, []
    for part, old, source, key, diagram in figures:
        identifier, url = _identity(
            key,
            source,
            diagram,
            tuple(g for g in generated if g.get("asset_key") == key),
        )
        owner = "condition" if part == "condition" else "solution"
        image, asset_changes = _attach(old, key, identifier, url, owner)
        changes.extend(asset_changes)
        if owner == "solution":
            pictures[part] = "<center>" + image + "</center>"
            keys.append(key)
        elif asset_changes:
            soup = BeautifulSoup(condition["html"], "html.parser")
            original = soup.find("img")
            if original is None:
                raise ContentPlanError("the original condition figure is required")
            original.replace_with(BeautifulSoup(image, "html.parser").img)
            change = rewrite(
                _targeted(condition),
                "condition",
                condition.get("title", "Условие"),
                str(soup),
            )
            change["value"]["asset_keys"] = [key]
            changes.append(change)
    return model, height_only, tuple(changes), pictures, tuple(keys)
