"""Reuse compatible unnumbered area and triangle-incircle diagrams."""

from . import static_figures
from .incircle_model import read_question

SOURCES = {
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
DETAILS = {"tangent_perimeter": (("detail", "dadd91a7-4bdc-45f4-a167-bf8fd458a747"),)}


def selection(context):
    return static_figures.selection(context, read_question, SOURCES, DETAILS, {})


def diagram_specs(context):
    selection(context)
    return ()


def prepare(context, generated):
    return static_figures.prepare(
        context, generated, read_question, SOURCES, DETAILS, {}
    )
