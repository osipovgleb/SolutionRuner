"""Reuse audited circles and labels; prepare verified local figure corrections."""

import json
from copy import deepcopy
from pathlib import Path

import sympy as sp

from ..probability import solution_diagrams
from ..word_problems.common import UnsupportedCondition, section
from .exam_input import read as read_exam
from .exam_trigonometric_circle_caption import (
    angle_caption,
    point_caption,
    series_caption,
)
from .exam_trigonometric_circle_caption import (
    selection_proof as _exported_selection_proof,
)
from .exam_trigonometric_panels import sources as panel_sources
from .exam_trigonometric_prepared_circle import recipe, source_less

selection_proof = _exported_selection_proof


DIRECTORY = Path(__file__).parent / "assets/exam-trigonometry"
CIRCLES = json.loads((DIRECTORY / "source-circles.json").read_text())
LINES = json.loads((DIRECTORY / "source-lines.json").read_text())
RASTERS = json.loads((DIRECTORY / "source-rasters.json").read_text())
SOURCES = CIRCLES | LINES | RASTERS
KEY = "exam_trig_circle"


def source(context):
    from .exam_trigonometric_log_selection import source as dual_source

    dual = dual_source(context)
    if dual is not None:
        return dual
    from .exam_trigonometric_log_figures import sources as log_sources

    log_figures = log_sources(context)
    if log_figures is not None:
        return log_figures[0]
    from .exam_trigonometric_auxiliary_figures import sources

    figures = sources(context)
    if figures is not None:
        return figures[0]
    content = context.get("normalized_content") or {}
    assets = content.get("assets", [])
    generated = [a for a in assets if a.get("asset_key") == KEY]
    originals = [a for a in assets if a.get("asset_key") != KEY]
    if (
        len(originals) != 1
        or len(generated) > 1
        or originals[0].get("asset_id") not in SOURCES
    ):
        raise UnsupportedCondition(
            "one mathematically audited source circle is required"
        )
    asset = originals[0]
    entry = SOURCES[asset["asset_id"]]
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
    from .exam_trigonometric_single import read as read_single

    if not (context.get("normalized_content") or {}).get("assets"):
        return read_single(context) or read_exam(context)
    if source_less(context):
        if recipe(context) is None:
            raise UnsupportedCondition(
                "the prepared circle must match a reviewed equation and interval"
            )
    elif panel_sources(context) is None:
        source(context)
    content = context["normalized_content"]
    prepared = deepcopy(context)
    prepared["normalized_content"]["assets"] = []
    copied_solution = section(prepared["normalized_content"], "solution")
    if copied_solution is not None:
        copied_solution["asset_keys"] = []
    _parts, formula, interval, bounds = read_single(prepared) or read_exam(prepared)
    return (
        tuple(section(content, key) for key in ("condition", "answer", "solution")),
        formula,
        interval,
        bounds,
    )


def validate(entry, a):
    from .exam_trigonometric_domain import validate_circle_domain
    from .exam_trigonometric_reciprocal_ratio import validate_axis

    validate_circle_domain(entry, a)
    if "log_domain_conditions" in entry:
        from .exam_trigonometric_log_product import conditions

        power_log = (
            a.power_polynomial is not None
            and a.power_polynomial.log_denominator is not None
        )
        if (
            a.log_product is None and a.log_polynomial is None and not power_log
        ) or entry["log_domain_conditions"] != [
            [str(e), relation] for e, relation in conditions(a)
        ]:
            raise UnsupportedCondition(
                "the source figure must retain its original log domain"
            )
    validate_axis(entry, a)
    if a.single_part:
        from .exam_trigonometric_single import validate_circle

        validate_circle(entry, a)
        return
    if entry.get("selection_kind") == "all_roots":
        if (
            (
                a.strict_quotient is not None
                and entry.get("figure_role") == "derivation"
                and a.selection_method == "progressions"
                and a.image_position != "selection"
            )
            or (
                a.radical_product is not None
                and a.radical_product.root_offset.is_negative
                and entry.get("radical_product_domain")
                and entry.get("figure_role") == "derivation"
                and a.image_position != "selection"
            )
            or (
                a.log_product is not None
                and (
                    entry.get("figure_role") == "derivation"
                    or (
                        entry.get("figure_role") == "alternative"
                        and a.log_product.radical is not None
                        and a.log_product.radical.alternative
                    )
                )
                and a.image_position != "selection"
            )
        ):
            from .exam_trigonometric_single import validate_circle

            validate_circle(entry, a)
            return
        raise UnsupportedCondition(
            "a full-root figure must not stand in for interval selection"
        )
    if "complete_residues" in entry:
        from .exam_trigonometric_inverse import decode

        if tuple(decode(q) for q in entry["complete_residues"]) != a.residues:
            raise UnsupportedCondition(
                "the prepared figure must preserve the complete root set"
            )
    if (
        entry.get("prepared_kind") == "number_line"
        and a.selection_method != "number_line"
    ):
        raise UnsupportedCondition(
            "the prepared number line requires its reviewed selection method"
        )
    if entry.get("figure_kind") == "number_line":
        from .exam_trigonometric_number_line import validate as validate_line

        return validate_line(entry, a)
    from .exam_trigonometric_inverse import decode

    expected = tuple(decode(q) for q in entry["residues"])
    bounds = tuple(decode(q) for q in entry["bounds"][:2]) + tuple(entry["bounds"][2:])
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
    if entry.get("label_scope") == "periodic" or "isolated_roots" in entry:
        from .exam_trigonometric_number_line import validate_isolated

        validate_isolated(entry, a)
    if entry.get("label_scope") == "periodic":
        from .exam_trigonometric import select

        selected = select(a.series, a.bounds)[0]
    scope = entry.get("point_scope", "all")
    if scope == "selected":
        from .exam_inverse_bounds import validate as validate_bound
        from .exam_trigonometric_inverse import ordered, turn

        for root in selected:
            validate_bound(root)
        residues = ordered(turn(q) for q in selected)
    elif scope != "all":
        raise UnsupportedCondition("unknown circle point scope")
    if residues != expected or actual_bounds != bounds or selected != labels:
        raise UnsupportedCondition(
            "the circle points, interval and labels must match the computed equation exactly"
        )


def diagram_specs(context):
    from .exam_trigonometric_log_selection import diagram_specs as dual_specs

    dual = dual_specs(context)
    if dual is not None:
        return dual
    if panel_sources(context) is not None:
        return ()
    if source_less(context):
        entry = recipe(context)
        return (
            (solution_diagrams.spec(KEY, (DIRECTORY / entry["file"]).read_text()),)
            if entry
            else ()
        )
    _, entry = source(context)
    if not entry.get("corrected_file"):
        return ()
    return (
        solution_diagrams.spec(KEY, (DIRECTORY / entry["corrected_file"]).read_text()),
    )


def image(context, a, generated, *, parent_html=""):
    from .exam_trigonometric_log_selection import image as dual_image
    from .exam_trigonometric_log_selection import source as dual_source

    if dual_source(context) is not None:
        return dual_image(context, a, generated)
    from .exam_trigonometric_log_figures import image as log_image
    from .exam_trigonometric_log_figures import sources as log_sources

    log_figures = log_sources(context)
    if log_figures is not None:
        return log_image(context, a, generated, log_figures, parent_html=parent_html)
    from .exam_trigonometric_auxiliary_figures import image as auxiliary_image
    from .exam_trigonometric_auxiliary_figures import sources

    auxiliary = sources(context)
    if auxiliary is not None:
        return auxiliary_image(context, a, generated, auxiliary)
    panels = panel_sources(context)
    if panels is not None:
        from .exam_trigonometric_panels import image as panel_image

        if generated:
            raise UnsupportedCondition(
                "compatible partition circles need no generated duplicates"
            )
        return panel_image(context, a, panels)
    if source_less(context):
        if a.strict_quotient is not None and a.strict_quotient.stage != "none":
            raise UnsupportedCondition(
                "the reviewed strict-denominator figure is required"
            )
        entry = recipe(context)
        if entry is not None:
            if a.selection_method != "circle":
                raise UnsupportedCondition(
                    "the prepared circle requires the reviewed circle-selection method"
                )
            validate(entry, a)
            markup, key, changes = solution_diagrams.image(
                context["normalized_content"],
                KEY,
                "Окружность для отбора корней",
                svg=(DIRECTORY / entry["file"]).read_text(),
                generated=generated,
            )
            if entry.get("point_scope") == "selected":
                markup += (
                    "<p>На окружности отмечены только корни указанного промежутка.</p>"
                )
            return markup + point_caption(entry, a), key, changes
        if a.global_radical is not None and a.selection_method == "global_domain":
            return "", "", []
        if a.selection_method not in ("inequalities", "progressions", "neighbors"):
            raise UnsupportedCondition("circle selection requires its source figure")
        return "", "", []
    asset, entry = source(context)
    validate(entry, a)
    alt = (
        "Числовая прямая для отбора корней"
        if entry.get("prepared_kind", entry.get("figure_kind")) == "number_line"
        else "Окружность для отбора корней"
    )
    if entry.get("corrected_file"):
        markup, key, changes = solution_diagrams.image(
            context["normalized_content"],
            KEY,
            alt,
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
        alt,
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
