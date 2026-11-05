"""Render the reviewed orthogonal distance, degree-angle or tangent parent method."""

from ..core.errors import ContentPlanError
from . import orthogonal_element_angles, orthogonal_element_distance


def render(model, picture=""):
    if model.mode in {"distance", "distance_squared"}:
        return orthogonal_element_distance.render(model, picture)
    if model.mode == "angle":
        return orthogonal_element_angles.angle(model, picture)
    if model.mode == "tangent":
        return orthogonal_element_angles.tangent(model, picture)
    raise ContentPlanError("one reviewed orthogonal element quantity is required")
