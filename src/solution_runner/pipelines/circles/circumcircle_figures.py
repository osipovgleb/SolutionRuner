"""Reuse the exact regular-triangle circumcircle constructions."""

from . import static_figures
from .circumcircle_model import read_question

SOURCES = {
    "radius_side": ("1725d5a4-9cd0-4fc3-903b-b5406c8fa4c0",),
    "side_radius": ("649e19b9-b2f8-4b20-b1dd-d55b8678de65",),
    "radius_height": ("91400a21-c013-48da-a644-d3bde6a3c153",),
    "height_radius": ("880b35c8-fb7d-462e-b041-a41ddce9bd5a",),
}


def diagram_specs(context):
    static_figures.selection(context, read_question, SOURCES, {}, {})
    return ()


def prepare(context, generated):
    return static_figures.prepare(context, generated, read_question, SOURCES, {}, {})
