"""Select exact compatible metric diagrams or relabel one reviewed body isometry."""

from ..core.errors import ContentPlanError
from ..probability.solution_diagrams import spec
from ..quadrilaterals.parallelogram.midpoint_figures import _attach
from ..triangles.isosceles.side_altitude_figures import _identity, condition_changes
from . import regular_prism_geometry as g
from .prism_metric_svg import render
from .prism_sources import DATA, source_bytes

KEY = "prism_metric_solution"


def mapped_scene(m, mapping):
    if m.kind == "metric_line_angle" and m.method != "cube_equilateral":
        return tuple(
            sorted(
                "".join(sorted(mapping[n] for n in g.names(line, 2)))
                for line in m.requested
            )
        )
    scene = tuple(mapping[n] for n in m.scene)
    return (
        (scene[0], *sorted(scene[1:]))
        if m.kind in {"metric_vertex_angle", "metric_tangent"}
        else tuple(sorted(scene))
    )


def validate(m, assets, owners):
    slots = DATA["metric_slots"][m.body]
    if set(assets) - set(slots) - {KEY}:
        raise ContentPlanError("the metric prism figure slot needs review")
    if KEY in assets and any(k != KEY and owners[k] == "solution" for k in assets):
        raise ContentPlanError("duplicate metric solution diagrams")
    for key, a in assets.items():
        if key == KEY:
            if owners[key] != "solution":
                raise ContentPlanError(
                    "a generated metric figure belongs to the solution"
                )
            continue
        record = DATA["figures"].get(a["asset_id"])
        if (
            not record
            or m.body not in record.get("metric_bodies", [])
            or [key, owners[key]] not in record["slots"]
            or owners[key] != slots[key]
        ):
            raise ContentPlanError(
                "the metric prism figure depicts another body or role"
            )
        source_bytes(a["asset_id"])


def choice(m, assets, owners):
    current = next(
        (a for k, a in assets.items() if owners[k] == "solution" and k != KEY), None
    )
    scenes = [
        s
        for s in DATA["metric_scenes"]
        if (s["body"], s["kind"], s["method"], tuple(s["scene"]))
        == (m.body, m.kind, m.method, m.scene)
    ]
    if scenes:
        chosen = next(
            (s for s in scenes if current and s["source"] == current["asset_id"]),
            scenes[0],
        )
        return chosen["source"], None
    for template in DATA["metric_templates"]:
        if (template["body"], template["kind"], template["method"]) != (
            m.body,
            m.kind,
            m.method,
        ):
            continue
        for mapping in g.isometries(m.body):
            # Map the requested scene back to the source, then invert the body isometry.
            if mapped_scene(m, mapping) == tuple(template["scene"]):
                inverse = {v: k for k, v in mapping.items()}
                return template["source"], spec(KEY, render(template, inverse))
    raise ContentPlanError("this metric prism scene needs a reviewed diagram")


def prepare(context, m, condition, assets, owners, generated):
    source, drawing = choice(m, assets, owners)
    changes = []
    pictures = {}
    condition_key = next(
        (k for k, r in DATA["metric_slots"][m.body].items() if r == "condition"), None
    )
    if condition_key:
        current = assets.get(condition_key, {})
        identifier = current.get("asset_id", DATA["metric_conditions"][m.body])
        changes.extend(
            condition_changes(
                context,
                condition,
                current,
                condition_key,
                identifier,
                "/assets/" + identifier,
                preserve_assets=("image_2", KEY),
            )
        )
    old = next((a for k, a in assets.items() if owners[k] == "solution"), None)
    key = (
        KEY
        if drawing
        else next(k for k, r in DATA["metric_slots"][m.body].items() if r == "solution")
    )
    identifier, url = _identity(key, source, drawing, generated)
    picture, attached = _attach(old, key, identifier, url, "solution")
    changes.extend(attached)
    pictures[key] = picture
    return m, tuple(changes), pictures, (key,)
