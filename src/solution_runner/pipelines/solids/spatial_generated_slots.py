"""Keep independently generated spatial illustrations in their native proof slots."""

from ..core.errors import ContentPlanError

SLOTS = {
    "triangle_prism_split_edge_projection_angle": ("image_1", "image_2", "image_3"),
    "triangle_pyramid_midpoint_skew_cosine": ("image_2",),
}
KEYS = {
    slot: "box_distance_solution_" + slot.removeprefix("image_")
    for slots in SLOTS.values()
    for slot in slots
}
PICTURES = {key: slot for slot, key in KEYS.items()}


def allowed(mode):
    return (
        {KEYS[slot] for slot in SLOTS[mode]}
        if mode in SLOTS
        else {"box_distance_solution"}
    )


def key(mode, slot):
    if mode not in SLOTS:
        return "box_distance_solution"
    if slot not in SLOTS[mode]:
        raise ContentPlanError("this spatial illustration has no reviewed generator")
    return KEYS[slot]


def asset_keys(mode, slot):
    if mode in SLOTS and slot not in SLOTS[mode]:
        return {slot}
    return {slot, key(mode, slot)}


def picture(key):
    return PICTURES.get(key, key)
