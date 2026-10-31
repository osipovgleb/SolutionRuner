"""Reuse two audited circles for a disjoint partition of one long interval."""

from dataclasses import replace

from ..probability import solution_diagrams
from ..word_problems.common import UnsupportedCondition
from ..word_problems.water_season_proof import inline
from .exam_trigonometric_inverse import decode


def sources(context):
    from .exam_trigonometric_circle import CIRCLES

    assets = (context.get("normalized_content") or {}).get("assets", [])
    if not any(
        CIRCLES.get(a.get("asset_id"), {}).get("partition_bounds") for a in assets
    ):
        return None
    if len(assets) != 2:
        raise UnsupportedCondition("both audited partition circles are required")
    result = []
    for index, asset in enumerate(assets):
        entry = CIRCLES.get(asset.get("asset_id"), {})
        if (
            entry.get("panel_index") != index
            or not entry.get("partition_bounds")
            or entry.get("corrected_file")
            or asset.get("asset_key") != "image_" + str(index + 1)
            or asset.get("url") != "/assets/" + asset.get("asset_id", "")
            or asset.get("kind") != "ordinary_image"
        ):
            raise UnsupportedCondition("the audited circle partition identity changed")
        result.append((asset, entry))
    if result[0][1]["partition_bounds"] != result[1][1]["partition_bounds"]:
        raise UnsupportedCondition("the circles must describe the same full interval")
    return tuple(result)


def bounds(values):
    return tuple(decode(q) for q in values[:2]) + tuple(values[2:])


def image(context, a, panels):
    from .exam_trigonometric import select
    from .exam_trigonometric_circle import validate
    from .exam_trigonometric_proof import pi

    full = bounds(panels[0][1]["partition_bounds"])
    first, second = (bounds(e["bounds"]) for _, e in panels)
    if (
        a.selection_method != "circle"
        or a.image_position != "selection"
        or a.scale != 1
        or a.translation
        or full != a.bounds
        or first[0] != full[0]
        or first[2] != full[2]
        or first[1] != second[0]
        or first[3] is not False
        or second[2] is not True
        or second[1] != full[1]
        or second[3] != full[3]
        or first[1] - first[0] != 2
        or not 0 < second[1] - second[0] <= 2
    ):
        raise UnsupportedCondition(
            "the two circles must partition the complete interval exactly"
        )
    html = "<p>Длина промежутка равна " + inline(pi(full[1] - full[0]))
    html += ". Используем две тригонометрические окружности для непересекающихся частей:</p>"
    html += '<section data-layout="media-row">'
    keys, changes, union = [], [], set()
    for (asset, entry), panel_bounds in zip(panels, (first, second), strict=True):
        selected, trace = select(a.series, panel_bounds)
        validate(
            entry, replace(a, bounds=panel_bounds, selected=selected, selections=trace)
        )
        union.update(selected)
        markup, key, edits = solution_diagrams.image(
            context["normalized_content"],
            asset["asset_key"],
            "Окружность для отбора корней",
            source_id=asset["asset_id"],
        )
        interval = (
            ("[" if panel_bounds[2] else "(")
            + pi(panel_bounds[0])
            + ";"
            + pi(panel_bounds[1])
            + ("]" if panel_bounds[3] else ")")
        )
        html += (
            '<section data-layout="media-item">'
            + markup
            + "<p>"
            + inline(interval)
            + ".</p></section>"
        )
        keys.append(key)
        changes.extend(edits)
    if tuple(sorted(union)) != a.selected:
        raise UnsupportedCondition(
            "the two circle selections must recover every selected root"
        )
    return html + "</section>", tuple(keys), changes
