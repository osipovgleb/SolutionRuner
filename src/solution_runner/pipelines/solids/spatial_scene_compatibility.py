"""Check reviewed semantic and numeric scene constraints before exact reuse."""

import sympy as sp


def scene_matches(model, entry, slot):
    if model.mode == "ratio_plane_angle" and entry.get(
        "condition_names", ["K", "M"]
    ) != list(model.names or ("K", "M")):
        return False
    if (
        "half_position" in entry
        and sp.sign(model.q["fraction"] - sp.Rational(1, 2)) != entry["half_position"]
    ):
        return False
    if model.mode == "square_perpendicular_section_ratio":
        purpose = (
            "coordinate"
            if slot == model.symbols.get("coordinate_slot")
            else "geometric"
        )
        if entry.get("purpose") != purpose:
            return False
    if model.mode in {
        "ratio_plane_distance",
        "square_vertical_vertex_area",
        "trapezoid_prism_pentagon_area",
    } and entry.get("method") != model.symbols.get("method"):
        return False
    if entry.get("requires_rhombus") and not model.q["rhombus"]:
        return False
    if entry.get("reusable") is False:
        return False
    if entry.get("before_center") and model.q["center_side"] <= 0:
        return False
    if any(
        sp.simplify(model.q[key] - sp.sympify(value)) != 0
        for key, value in entry.get("measurements", {}).items()
    ):
        return False
    if entry.get("before_S") and model.q["ratio"] <= 1:
        return False
    if (
        "equal_lengths" in entry
        and sp.simplify(
            model.q[entry["equal_lengths"][0]] - model.q[entry["equal_lengths"][1]]
        )
        != 0
    ):
        return False
    if entry.get("top_foot") and not (0 < model.q["foot"] < 1):
        return False
    if "names_prefix" in entry and entry["names_prefix"] != list(
        model.names[: len(entry["names_prefix"])]
    ):
        return False
    if "names" in entry and entry["names"] != list(model.names):
        return False
    if entry.get("interior") and not (0 < model.q["foot"] < 1):
        return False
    return "squares" not in entry or (
        entry["squares"] == [str(v) for v in model.squares]
        and entry["names"] == list(model.names)
    )
