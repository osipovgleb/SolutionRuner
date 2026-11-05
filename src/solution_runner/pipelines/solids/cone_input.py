"""Read the complete cone condition using the existing strict geometry markup reader."""

from ..core.errors import ContentPlanError
from ..triangles.right.altitude_input import _text
from ..triangles.right.altitude_solver import AltitudeSolveError


def text(html, source=None):
    if not isinstance(html, str):
        raise ContentPlanError("complete cone condition HTML is required")
    try:
        return (
            _text(html, source, labels="ABCOShlrdVRH")
            .replace("ё", "е")
            .replace("π", r"\pi")
            .replace("B ответе", "В ответе")
            .replace("B сосуд", "В сосуд")
        )
    except AltitudeSolveError as exc:
        raise ContentPlanError(str(exc)) from exc
