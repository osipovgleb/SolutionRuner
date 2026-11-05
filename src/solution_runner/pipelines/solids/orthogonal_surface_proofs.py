"""Select all supplied parent surface methods in their original order."""

from ..core.errors import ContentPlanError
from . import orthogonal_surface_bbox as bbox
from . import orthogonal_surface_glued as glued


def methods(m, style):
    kind = style["method"]
    if kind in {"reduced_xy", "reduced_xz", "reduced_yz"}:
        return (bbox.reduced(m, kind),)
    if kind == "corner_grouped":
        return bbox.unchanged(m), bbox.grouped(m)
    if kind == "corner_nine":
        return bbox.unchanged(m), bbox.nine_faces(m)
    if kind in {"front_notch", "front_groove"}:
        return (bbox.groove(m, kind),)
    if kind in {"glued_two", "glued_three"}:
        return (glued.glued(m, style),)
    if kind == "shelf_both":
        return glued.glued(m, style), glued.shelf_bbox(m)
    if kind == "hole_both":
        return glued.hole(m), glued.hole_faces(m)
    if kind == "cancel_central":
        return (glued.cancelled(m, style),)
    raise ContentPlanError("an explicit reviewed surface method is required")


def render(m, style):
    parts = methods(m, style)
    if len(parts) == 1:
        return parts[0]
    return (
        "<p><b>Первый способ.</b></p>"
        + parts[0]
        + "<p><b>Второй способ.</b></p>"
        + parts[1]
    )
