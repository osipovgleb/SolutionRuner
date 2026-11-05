"""Retain reviewed cube lettering and paint the actual box's helper segments."""

import hashlib
import json
from importlib.resources import files

from ..core.errors import ContentPlanError
from . import box_coordinates as c
from .box_distance_geometry import blue
from .box_svg import render_svg
from .distance_sources import source_bytes

TEMPLATE_SHA256 = "9d139157ce639d958efa5c75928fa023cc901e1afadbb43d2a75fdfd5b4adca3"


def template(source):
    raw = files(__package__).joinpath("assets/box-distance-templates.json").read_bytes()
    if hashlib.sha256(raw).hexdigest() != TEMPLATE_SHA256:
        raise ContentPlanError("the reviewed spatial diagram geometry changed")
    return json.loads(raw)[source]


def figure_svg(model, source, role):
    required, allowed = blue(model, role)
    segments = (
        allowed
        if model.mode == "distance"
        and len(c.axes(model.requested)) == 2
        and role == "solution"
        else required
    )
    return render_svg(source_bytes(source), template(source), model.squares, segments)
