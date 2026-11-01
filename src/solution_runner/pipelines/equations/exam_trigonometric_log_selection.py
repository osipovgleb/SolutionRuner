"""Keep both reviewed number-line and circle selections, reusing existing assets."""

from dataclasses import replace

from ..probability import solution_diagrams
from ..word_problems.common import UnsupportedCondition

KEY = "exam_trig_number_line"


def source(context):
    from .exam_trigonometric_circle import CIRCLES, LINES

    assets = (context.get("normalized_content") or {}).get("assets", [])
    matches = [
        (a, CIRCLES[a["asset_id"]])
        for a in assets
        if CIRCLES.get(a.get("asset_id"), {}).get("log_selection_line")
    ]
    if not matches:
        return None
    if len(matches) != 1:
        raise UnsupportedCondition(
            "one reviewed circle must accompany the number-line method"
        )
    asset, entry = matches[0]
    if asset.get("asset_key") != entry["original_key"]:
        raise UnsupportedCondition(
            "the original alternate-selection circle key changed"
        )
    expected = {asset["asset_id"]}
    if entry["has_original_line"]:
        expected.add(entry["log_selection_line"]["source_id"])
    originals = [a for a in assets if a.get("asset_key") != KEY]
    generated = [a for a in assets if a.get("asset_key") == KEY]
    if (
        len(originals) != len(expected)
        or {a.get("asset_id") for a in originals} != expected
        or len(generated) > 1
        or (entry["has_original_line"] and generated)
    ):
        raise UnsupportedCondition(
            "the exact original line/circle inventory is required"
        )
    for a in assets:
        if (
            not isinstance(a.get("asset_id"), str)
            or a.get("kind") != "ordinary_image"
            or a.get("url") != "/assets/" + a["asset_id"]
        ):
            raise UnsupportedCondition(
                "the alternate-selection figure identity changed"
            )
    if entry["has_original_line"]:
        line = next(a for a in originals if a["asset_id"] != asset["asset_id"])
        if line["asset_key"] != "image_1" or line["asset_id"] not in LINES:
            raise UnsupportedCondition(
                "the original first-method number line is required"
            )
    if (
        generated
        and entry["log_selection_line"].get("source_id")
        and generated[0]["asset_id"] != entry["log_selection_line"]["source_id"]
    ):
        raise UnsupportedCondition(
            "the compatible parent line must be reused without a duplicate asset"
        )
    return asset, entry


def diagram_specs(context):
    from .exam_trigonometric_circle import DIRECTORY

    found = source(context)
    if found is None:
        return None
    model = found[1]["log_selection_line"]
    return (
        (solution_diagrams.spec(KEY, (DIRECTORY / model["file"]).read_text()),)
        if model.get("file")
        else ()
    )


def line_image(content, entry, generated):
    from .exam_trigonometric_circle import DIRECTORY

    model = entry["log_selection_line"]
    if model.get("file"):
        return solution_diagrams.image(
            content,
            KEY,
            "Отбор корней на числовой оси",
            svg=(DIRECTORY / model["file"]).read_text(),
            generated=generated,
        )
    if generated:
        raise UnsupportedCondition("an existing compatible number line needs no upload")
    aid = model["source_id"]
    existing = [a for a in content["assets"] if a["asset_id"] == aid]
    if existing:
        return solution_diagrams.image(
            content,
            existing[0]["asset_key"],
            "Отбор корней на числовой оси",
            source_id=aid,
        )
    asset = {
        "asset_key": KEY,
        "asset_id": aid,
        "url": "/assets/" + aid,
        "kind": "ordinary_image",
        "alt": "Отбор корней на числовой оси",
        "parent_target_id": "section:solution:1",
        "position": 0,
    }
    copied = {**content, "assets": [*content["assets"], asset]}
    html, key, _ = solution_diagrams.image(copied, KEY, asset["alt"], source_id=aid)
    return (
        html,
        key,
        [
            {
                "transformation_target_id": "asset:" + KEY,
                "operation": "add",
                "value": {**asset, "html": html},
            }
        ],
    )


def image(context, a, generated):
    from .exam_trigonometric import select
    from .exam_trigonometric_circle import validate
    from .exam_trigonometric_inverse import decode

    asset, entry = source(context)
    model = entry["log_selection_line"]
    if (
        a.log_polynomial is None
        or not a.log_polynomial.alternative_selection
        or a.selection_method != "log_dual_selection"
    ):
        raise UnsupportedCondition(
            "both original interval-selection methods must be preserved"
        )
    bounds = tuple(decode(v) for v in model["bounds"][:2]) + tuple(model["bounds"][2:])
    if (
        bounds != a.bounds
        or tuple(map(decode, model["residues"]))
        != select(a.series, (0, 2, True, False))[0]
        or tuple(map(decode, model["labels"])) != a.selected
    ):
        raise UnsupportedCondition(
            "the number line must match the complete roots, interval and selected labels"
        )
    validate(entry, a)
    first, key, changes = line_image(context["normalized_content"], entry, generated)
    second, other, edits = solution_diagrams.image(
        context["normalized_content"],
        asset["asset_key"],
        "Отбор корней на окружности",
        source_id=asset["asset_id"],
    )
    return (first, second), (key, other), [*changes, *edits]


def selection(a, images):
    from ..probability.common import line
    from ..word_problems.water_season_proof import inline
    from .exam_trigonometric_circle import selection_proof
    from .exam_trigonometric_proof import pi

    first, second = images
    html = (
        "<p>Найдём на числовой оси корни, лежащие на промежутке "
        + inline(a.interval)
        + ". Отметим серии корней и границы промежутка:</p>"
        + first
    )
    html += "<p>Из расположения отметок между границами получаем:</p>"
    for q in a.selected:
        html += line(
            pi(a.bounds[0])
            + (r"\le" if a.bounds[2] else "<")
            + pi(q)
            + (r"\le" if a.bounds[3] else "<")
            + pi(a.bounds[1])
        )
    html += "<p>Приведём другое решение пункта б). Выясним, какие из найденных корней принадлежат тому же промежутку, при помощи тригонометрической окружности:</p>"
    return html + selection_proof(
        replace(a, selection_method="circle", image_position="selection"), second
    )
