"""Reviewed prism section scenes, methods and point-label variants."""

from dataclasses import replace

RULES = {
    "solid-square-prism-diagonal-ratio-area": "square_prism_ratio_area",
    "solid-square-prism-rhombus-section": (
        "square_prism_rhombus_height",
        "square_prism_rhombus_area",
    ),
    "solid-parallelogram-prism-similar-trapezoid": "parallelogram_prism_trapezoid_area",
    "solid-trapezoid-prism-midpoint-pentagon": "trapezoid_prism_pentagon_area",
}
ROLES = {
    "square_prism_ratio_area": (
        ("solution", "image_1", "30db0046-042a-457a-a985-d8c6a8ed58be"),
        ("solution", "image_2", "c16a14a8-519a-4fd1-b782-2d7a33cfdb30"),
    ),
    "square_prism_rhombus_height": (
        ("solution", "image_1", "83ebc220-f0fc-4ce1-a003-2b01c4fb3394"),
    ),
    "square_prism_rhombus_area": (
        ("solution", "image_1", "83ebc220-f0fc-4ce1-a003-2b01c4fb3394"),
    ),
    "parallelogram_prism_trapezoid_area": (
        ("solution", "image_1", "c7f95b72-4534-41a2-8baa-54fa5c0e1aca"),
    ),
    "trapezoid_prism_pentagon_area": (
        ("solution", "image_1", "33d73826-53b8-420c-9560-9ff4f13eac97"),
    ),
}


def reviewed_model(model):
    if model.mode != "trapezoid_prism_pentagon_area":
        return None
    return replace(model, symbols={"method": "projection"})


def roles(model):
    if model.mode == "square_prism_ratio_area" and model.names == ("K",):
        return (
            ("solution", "image_1", "05fff0df-e7c0-4cbd-98a4-846c1c7f2865"),
            ("solution", "image_2", "64ca8f94-e81d-41b5-b5b8-b50768512bdc"),
        )
    if model.mode == "trapezoid_prism_pentagon_area" and model.names == ("G", "F"):
        return (("solution", "image_1", "8e8e20aa-04ee-4513-8a9c-4a84ca87ab46"),)
    return ROLES.get(model.mode)
