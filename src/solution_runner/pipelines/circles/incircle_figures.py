"""Reuse compatible unnumbered area and triangle-incircle diagrams."""

from . import static_figures
from .incircle_model import read_question

SOURCES = {
    "trapezoid_legs": ("49629729-cca6-45a3-847b-718059b3f287",),
    "trapezoid_perimeter": ("49629729-cca6-45a3-847b-718059b3f287",),
    "right_trapezoid_radius": ("dd32ef1c-0671-4408-abb1-7a483841fc55",),
    "tangential_quad": (
        "af6e87fa-5536-44f0-967b-62be25dede86",
        "3ce39918-b981-4707-ba88-4b951758f04c",
    ),
    "tangent_cuts": (
        "cb3e01b8-f2f7-443f-94be-5d07b0304b92",
        "2ea27720-dba3-42e1-a18d-9aaea689a2ce",
    ),
    "rhombus_radius": ("1446766a-f13a-4866-8904-d7fc5f49f0c8",),
    "rhombus_side": ("1446766a-f13a-4866-8904-d7fc5f49f0c8",),
    "hexagon_side": ("bd99ce14-74a9-4790-939e-ba8be82ea490",),
    "hexagon_radius": (
        "0a1a3de1-9bce-43ad-8c5e-930245e4d3a5",
        "73e2eef4-1919-4a74-8d62-2617d521c7c9",
    ),
    "polygon_area": ("68bb519a-757f-4f57-9dc1-90d1165e7bb1",),
    "triangle_area": ("5408d585-4bb2-49e0-a00d-cd1b8cdaf111",),
    "triangle_perimeter": ("5408d585-4bb2-49e0-a00d-cd1b8cdaf111",),
    "equilateral_radius_height": ("3a6977ef-d97f-474e-8c54-d07758af03ba",),
    "equilateral_height_radius": ("3a6977ef-d97f-474e-8c54-d07758af03ba",),
    "equilateral_radius_side": ("3a6977ef-d97f-474e-8c54-d07758af03ba",),
    "equilateral_side_radius": ("3a6977ef-d97f-474e-8c54-d07758af03ba",),
    "isosceles_right_radius": ("1fdb6041-f91e-4585-866b-d66465fdad18",),
    "right_radius": ("7b871ed2-dbff-4130-8aa2-ab68658333a9",),
    "isosceles_radius": ("2e28b07d-6116-4f98-bbe6-99edd9064cac",),
    "tangent_perimeter": ("515f4048-fd47-41f8-a462-984e0050be88",),
}
DETAILS = {
    "tangent_cuts": (("equal_tangents", "36e82f8a-fe0b-4edc-9382-7cdb65eb3d71"),),
    "tangent_perimeter": (("detail", "dadd91a7-4bdc-45f4-a167-bf8fd458a747"),),
    "rhombus_radius": (("height", "e1f42826-e0fc-4d65-9663-0fb90911f70b"),),
    "rhombus_side": (("height", "e1f42826-e0fc-4d65-9663-0fb90911f70b"),),
    "hexagon_side": (("tangent", "7058b1bc-557c-4cb1-b281-9ef2910ae12a"),),
    "hexagon_radius": (
        ("cosine", "2c1f434b-33bb-40e4-93d9-4d6229d84576"),
        ("pythagoras", "1a91c9e3-29ac-433e-b6cb-c3363977f641"),
        ("sine", "59fee103-a830-4872-91d6-070344ecd5b1"),
    ),
}


def selection(context):
    return static_figures.selection(context, read_question, SOURCES, DETAILS, {})


def diagram_specs(context):
    selection(context)
    return ()


def prepare(context, generated):
    return static_figures.prepare(
        context, generated, read_question, SOURCES, DETAILS, {}
    )
