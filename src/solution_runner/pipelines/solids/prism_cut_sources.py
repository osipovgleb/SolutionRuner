"""Reviewed prism section scenes, methods and point-label variants."""

from dataclasses import replace

RULES = {
    "solid-triangle-prism-midpoint-section-height": "triangle_prism_oblique_height",
    "solid-triangle-prism-perpendicular-face-section": (
        "triangle_prism_perpendicular_area",
        "triangle_prism_perpendicular_height",
    ),
    "solid-box-opposite-vertex-section": "box_opposite_section_area",
    "solid-box-diagonal-normal-bisector": "box_diagonal_bisector_ratio",
    "solid-square-prism-diagonal-ratio-area": "square_prism_ratio_area",
    "solid-square-prism-rhombus-section": (
        "square_prism_rhombus_height",
        "square_prism_rhombus_area",
    ),
    "solid-parallelogram-prism-similar-trapezoid": "parallelogram_prism_trapezoid_area",
    "solid-trapezoid-prism-midpoint-pentagon": "trapezoid_prism_pentagon_area",
}
ROLES = {
    "triangle_prism_oblique_height": (
        ("solution", "image_1", "0b77ea55-724c-4e60-a300-968509cf9493"),
    ),
    "triangle_prism_perpendicular_area": (
        ("solution", "image_1", "745eb769-48d1-4877-9698-69505ba698ab"),
    ),
    "triangle_prism_perpendicular_height": (
        ("solution", "image_1", "745eb769-48d1-4877-9698-69505ba698ab"),
    ),
    "box_opposite_section_area": (
        ("solution", "image_1", "61c09fa1-4d10-41b3-9e16-633f88d9baaa"),
    ),
    "box_diagonal_bisector_ratio": tuple(
        ("solution", "image_" + str(i), source)
        for i, source in enumerate(
            (
                "026ff245-e5c0-4bf9-8a23-e05854ab5bf3",
                "9f1db910-ae3b-479e-9886-e1a52b630e7a",
                "9222e697-b218-43cb-a2c0-d90b606b033c",
                "c89aa9e7-67de-4604-8b54-bf79c13cd6c9",
            ),
            1,
        )
    ),
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


def reviewed_model(model, assets):
    if model.mode in {
        "triangle_prism_perpendicular_area",
        "triangle_prism_perpendicular_height",
        "box_opposite_section_area",
    }:
        return replace(
            model, symbols={"second_figure": "yes" if "image_2" in assets else "no"}
        )
    if model.mode != "trapezoid_prism_pentagon_area":
        return None
    return replace(model, symbols={"method": "projection"})


def roles(model):
    if model.mode in {
        "triangle_prism_perpendicular_area",
        "triangle_prism_perpendicular_height",
    }:
        source = (
            "21b9d632-f537-4b72-bca3-dce94e1dfee9"
            if 2 * model.q["r"] < 1
            else "745eb769-48d1-4877-9698-69505ba698ab"
        )
        main = (("solution", "image_1", source),)
        return main + (
            (("solution", "image_2", "09b933d5-7b11-49d0-b20d-a3d56c967100"),)
            if model.symbols.get("second_figure") == "yes"
            else ()
        )
    if model.mode == "box_opposite_section_area":
        main, second = (
            (
                "61c09fa1-4d10-41b3-9e16-633f88d9baaa",
                "22fd0ad1-75b3-4891-a104-44960129fc86",
            )
            if model.names[0] == "W"
            else (
                "3686f0aa-d823-48e8-a5cd-62b9fa298778",
                "8faa95c4-9b85-464e-ba8b-a51ca495fc40",
            )
        )
        return (("solution", "image_1", main),) + (
            (("solution", "image_2", second),)
            if model.symbols.get("second_figure") == "yes" and model.q["rhombus"]
            else ()
        )
    if model.mode == "square_prism_ratio_area" and model.names == ("K",):
        return (
            ("solution", "image_1", "05fff0df-e7c0-4cbd-98a4-846c1c7f2865"),
            ("solution", "image_2", "64ca8f94-e81d-41b5-b5b8-b50768512bdc"),
        )
    if model.mode == "trapezoid_prism_pentagon_area" and model.names == ("G", "F"):
        return (("solution", "image_1", "8e8e20aa-04ee-4513-8a9c-4a84ca87ab46"),)
    return ROLES.get(model.mode)
