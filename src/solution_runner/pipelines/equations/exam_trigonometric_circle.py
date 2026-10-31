"""Reuse audited circles and labels; prepare verified local figure corrections."""

import json
from copy import deepcopy
from pathlib import Path

import sympy as sp

from ..probability import solution_diagrams
from ..word_problems.common import UnsupportedCondition, section
from .exam_input import read as read_exam

DIRECTORY = Path(__file__).parent / "assets/exam-trigonometry"
CIRCLES = json.loads((DIRECTORY / "source-circles.json").read_text())
KEY = "exam_trig_circle"


def source(context):
    content = context.get("normalized_content") or {}
    assets = content.get("assets", [])
    generated = [a for a in assets if a.get("asset_key") == KEY]
    originals = [a for a in assets if a.get("asset_key") != KEY]
    if (
        len(originals) != 1
        or len(generated) > 1
        or originals[0].get("asset_id") not in CIRCLES
    ):
        raise UnsupportedCondition(
            "one mathematically audited source circle is required"
        )
    asset = originals[0]
    entry = CIRCLES[asset["asset_id"]]
    if (
        asset.get("asset_key") != "image_1"
        or asset.get("url") != "/assets/" + asset["asset_id"]
        or asset.get("kind") != "ordinary_image"
    ):
        raise UnsupportedCondition("the original circle identity changed")
    if generated and not entry.get("corrected_file"):
        raise UnsupportedCondition(
            "an unneeded generated circle must not replace a compatible source"
        )
    return asset, entry


def read(context):
    if not (context.get("normalized_content") or {}).get("assets"):
        return read_exam(context)
    source(context)
    content = context["normalized_content"]
    prepared = deepcopy(context)
    prepared["normalized_content"]["assets"] = []
    copied_solution = section(prepared["normalized_content"], "solution")
    if copied_solution is not None:
        copied_solution["asset_keys"] = []
    _parts, formula, interval, bounds = read_exam(prepared)
    return (
        tuple(section(content, key) for key in ("condition", "answer", "solution")),
        formula,
        interval,
        bounds,
    )


def validate(entry, a):
    from .exam_trigonometric_inverse import decode

    expected = tuple(decode(q) for q in entry["residues"])
    bounds = tuple(sp.Rational(q) for q in entry["bounds"][:2]) + tuple(
        entry["bounds"][2:]
    )
    labels = tuple(decode(q) for q in entry["labels"])
    residues, actual_bounds, selected = a.residues, a.bounds, a.selected
    if a.scale != 1 or a.translation:
        from .exam_trigonometric import select

        multiplier = sp.Rational(entry.get("circle_scale", "1"))
        if multiplier <= 0:
            raise UnsupportedCondition("the circle angle multiplier must be positive")
        residues = select(
            tuple((q * multiplier, p * multiplier) for q, p in a.series),
            (sp.Integer(0), sp.Integer(2), True, False),
        )[0]
        actual_bounds = tuple(q * multiplier for q in a.bounds[:2]) + a.bounds[2:]
        selected = tuple(q * multiplier for q in a.selected)
    scope = entry.get("point_scope", "all")
    if scope == "selected":
        from .exam_trigonometric_inverse import ordered

        if any(q.is_Rational is not True for q in selected):
            raise UnsupportedCondition(
                "a selected-only circle needs reviewed rational angles"
            )
        residues = ordered(q % 2 for q in selected)
    elif scope != "all":
        raise UnsupportedCondition("unknown circle point scope")
    if residues != expected or actual_bounds != bounds or selected != labels:
        raise UnsupportedCondition(
            "the circle points, interval and labels must match the computed equation exactly"
        )


def diagram_specs(context):
    if not (context.get("normalized_content") or {}).get("assets"):
        return ()
    _, entry = source(context)
    if not entry.get("corrected_file"):
        return ()
    return (
        solution_diagrams.spec(KEY, (DIRECTORY / entry["corrected_file"]).read_text()),
    )


def image(context, a, generated):
    if not context["normalized_content"].get("assets"):
        if a.selection_method != "inequalities":
            raise UnsupportedCondition("circle selection requires its source figure")
        return "", "", []
    asset, entry = source(context)
    validate(entry, a)
    if entry.get("corrected_file"):
        markup, key, changes = solution_diagrams.image(
            context["normalized_content"],
            KEY,
            "Окружность для отбора корней",
            svg=(DIRECTORY / entry["corrected_file"]).read_text(),
            generated=generated,
        )
        if entry.get("point_scope") == "selected":
            markup += (
                "<p>На окружности отмечены только корни указанного промежутка.</p>"
            )
        return markup, key, changes
    markup, key, changes = solution_diagrams.image(
        context["normalized_content"],
        "image_1",
        "Окружность для отбора корней",
        source_id=asset["asset_id"],
    )
    return (
        markup
        + point_caption(entry, a)
        + series_caption(entry, a)
        + angle_caption(entry, a),
        key,
        changes,
    )


def angle_caption(entry, a):
    from ..probability.common import line
    from ..word_problems.water_season_proof import inline
    from .exam_trigonometric_proof import pi

    multiplier = sp.Rational(entry.get("circle_scale", "1"))
    if multiplier == 1:
        return ""
    angle = sp.latex(multiplier * sp.Symbol("x", real=True))
    lo, hi, lc, uc = a.bounds
    html = (
        "<p>На окружности рассматриваем угол "
        + inline(angle)
        + ". Пересчитаем границы промежутка и выбранные корни:</p>"
    )
    html += line(
        pi(lo * multiplier)
        + (r"\le" if lc else "<")
        + angle
        + (r"\le" if uc else "<")
        + pi(hi * multiplier)
    )
    for q in a.selected:
        html += line(
            angle
            + "="
            + pi(q * multiplier)
            + r"\quad\Longleftrightarrow\quad x="
            + pi(q)
        )
    return html


def series_caption(entry, a):
    from ..probability.common import line
    from .exam_trigonometric import C
    from .exam_trigonometric_inverse import level_series
    from .exam_trigonometric_proof import series_lines

    marks = entry.get("series_marks")
    if not marks:
        return ""
    if (
        a.scale != sp.Rational(entry["series_angle"])
        or len(a.branches) != 1
        or a.branches[0].variable != C
        or {sp.Rational(m["value"]) for m in marks} != set(a.branches[0].values)
    ):
        raise UnsupportedCondition("the marked series must match all cosine levels")
    html = "<p>На рисунке обозначены серии:</p>"
    for mark in marks:
        if mark["label"] not in ("*", "**"):
            raise UnsupportedCondition("unknown source series label")
        series = tuple(
            (q / a.scale, p / a.scale)
            for q, p in level_series(C, sp.Rational(mark["value"]))
        )
        if any(s not in a.series for s in series):
            raise UnsupportedCondition("the circle series marker changed")
        html += "".join(
            line(text + r",\quad k\in\mathbb Z\quad(" + mark["label"] + ")")
            for text in series_lines(series)
        )
    return html


def point_caption(entry, a):
    from ..word_problems.water_season_proof import inline
    from .exam_trigonometric import S
    from .exam_trigonometric_inverse import decode, ordered
    from .exam_trigonometric_proof import formula

    letters = entry.get("point_letters")
    if not letters:
        return ""
    if (
        len(a.branches) != 1
        or ordered(decode(q) for q in letters.values()) != a.residues
    ):
        raise UnsupportedCondition(
            "the lettered circle must describe all computed roots"
        )
    variable = a.branches[0].variable
    function = sp.sin if variable == S else sp.cos
    groups = {}
    for letter, q in letters.items():
        value = sp.simplify(function(decode(q) * sp.pi))
        groups.setdefault(value, []).append(letter)
    return "".join(
        "<p>Корни уравнения "
        + inline(formula(variable) + "=" + sp.latex(value))
        + "изображаются точками "
        + " и ".join(names)
        + ".</p>"
        for value, names in groups.items()
    )
