"""Keep a log-product domain circle separate from its interval-selection circle."""

from dataclasses import replace

from ..probability import solution_diagrams
from ..word_problems.common import UnsupportedCondition


def sources(context):
    from .exam_trigonometric_circle import CIRCLES

    assets = (context.get("normalized_content") or {}).get("assets", [])
    if not any(
        (
            CIRCLES.get(a.get("asset_id"), {}).get("selection_companion")
            or CIRCLES.get(a.get("asset_id"), {}).get("alternative_companion")
        )
        for a in assets
    ):
        return None
    if len(assets) != 2:
        raise UnsupportedCondition(
            "both domain and selection source circles are required"
        )
    result = []
    for index, asset in enumerate(assets, 1):
        entry = CIRCLES.get(asset.get("asset_id"), {})
        if (
            not entry
            or asset.get("asset_key") != "image_" + str(index)
            or asset.get("url") != "/assets/" + asset.get("asset_id", "")
            or asset.get("kind") != "ordinary_image"
            or entry.get("corrected_file")
        ):
            raise UnsupportedCondition(
                "the log-product source figure identities changed"
            )
        result.append((asset, entry))
    first, second = result
    alternative = first[1].get("alternative_companion")
    if alternative:
        if (
            alternative != second[0]["asset_id"]
            or first[1].get("selection_kind") == "all_roots"
            or second[1].get("selection_kind") != "all_roots"
            or second[1].get("figure_role") != "alternative"
        ):
            raise UnsupportedCondition(
                "the alternate cases need their own full-root figure after selection"
            )
    elif (
        first[1].get("selection_kind") != "all_roots"
        or first[1].get("figure_role") != "derivation"
        or first[1]["selection_companion"] != second[0]["asset_id"]
        or second[1].get("selection_kind") == "all_roots"
    ):
        raise UnsupportedCondition(
            "the domain figure must keep its own selection companion"
        )
    return tuple(result)


def image(context, a, generated, figures):
    from .exam_trigonometric_circle import validate

    if (
        generated
        or a.log_product is None
        or a.selection_method != "circle"
        or a.image_position == "selection"
    ):
        raise UnsupportedCondition(
            "the reviewed log-product figures need separate original roles"
        )
    alternative = figures[0][1].get("alternative_companion") is not None
    if alternative and (
        a.log_product.radical is None or not a.log_product.radical.alternative
    ):
        raise UnsupportedCondition(
            "the full-root companion requires both reviewed radical-log methods"
        )
    markup, keys, changes = [], [], []
    for index, (asset, entry) in enumerate(figures):
        validate(
            entry,
            a
            if index == 0
            else replace(
                a, image_position="after-steps" if alternative else "selection"
            ),
        )
        html, key, edits = solution_diagrams.image(
            context["normalized_content"],
            asset["asset_key"],
            (
                "Окружность для отбора корней"
                if index == 0
                else "Окружность для проверки отдельных нулевых множителей"
            )
            if alternative
            else (
                "Окружность для проверки ОДЗ"
                if index == 0
                else "Окружность для отбора корней"
            ),
            source_id=asset["asset_id"],
        )
        markup.append(html)
        keys.append(key)
        changes.extend(edits)
    return tuple(markup), tuple(keys), changes
