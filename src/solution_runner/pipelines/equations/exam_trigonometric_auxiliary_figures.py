"""Keep interval selection and a separate geometric-system note in their own roles."""

from copy import deepcopy

import sympy as sp

from ..probability import solution_diagrams
from ..word_problems.common import UnsupportedCondition


def sources(context):
    from .exam_trigonometric_circle import CIRCLES, KEY

    assets = (context.get("normalized_content") or {}).get("assets", [])
    originals = [a for a in assets if a.get("asset_key") != KEY]
    if not any(
        CIRCLES.get(a.get("asset_id"), {}).get("figure_kind") == "auxiliary_system"
        for a in originals
    ):
        return None
    generated = [a for a in assets if a.get("asset_key") == KEY]
    if len(originals) != 2 or len(generated) > 1:
        raise UnsupportedCondition("both auxiliary-method source figures are required")
    result = []
    for index, asset in enumerate(originals, 1):
        entry = CIRCLES.get(asset.get("asset_id"), {})
        if (
            not entry
            or asset.get("asset_key") != "image_" + str(index)
            or asset.get("url") != "/assets/" + asset.get("asset_id", "")
            or asset.get("kind") != "ordinary_image"
        ):
            raise UnsupportedCondition("the auxiliary source identities changed")
        result.append((asset, entry))
    first, second = result
    if (
        second[1].get("figure_kind") != "auxiliary_system"
        or second[1].get("interval_asset_id") != first[0]["asset_id"]
        or second[1].get("corrected_file")
        or (generated and not first[1].get("corrected_file"))
    ):
        raise UnsupportedCondition(
            "the system figure needs its own reviewed interval companion"
        )
    return tuple(result)


def validate_system(entry, a):
    from .exam_trigonometric_auxiliary_notes import half_angle
    from .exam_trigonometric_domain import validate_circle_domain
    from .exam_trigonometric_inverse import decode

    half_angle(a)
    coefficients = tuple(map(sp.Rational, entry["equation_coefficients"]))
    from .exam_trigonometric_compile import C, S

    if (
        not a.auxiliary_notes
        or entry.get("bounds") is not None
        or sp.Rational(entry["circle_scale"]) != a.scale
        or coefficients != (a.raw.coeff(S), a.raw.coeff(C), a.raw.subs({S: 0, C: 0}))
        or tuple(map(decode, entry["residues"])) != a.residues
    ):
        raise UnsupportedCondition(
            "the geometric system must match the primary equation, angle and complete roots"
        )
    validate_circle_domain(entry, a)


def image(context, a, generated, figures):
    from .exam_trigonometric_circle import image as interval_image

    if not a.auxiliary_notes:
        raise UnsupportedCondition(
            "the two figures require the reviewed auxiliary-angle notes"
        )
    _, second = figures
    copied = deepcopy(context)
    copied["normalized_content"]["assets"] = [
        asset
        for asset in copied["normalized_content"]["assets"]
        if asset.get("asset_key") != "image_2"
    ]
    markup, key, changes = interval_image(copied, a, generated)
    validate_system(second[1], a)
    system, system_key, system_changes = solution_diagrams.image(
        context["normalized_content"],
        "image_2",
        "Геометрическое решение системы в угле " + str(a.scale) + "x",
        source_id=second[0]["asset_id"],
    )
    return (markup, system), (key, system_key), [*changes, *system_changes]
