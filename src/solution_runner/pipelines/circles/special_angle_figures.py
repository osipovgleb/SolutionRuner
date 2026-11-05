"""Exact radius-chord diagrams, with no unrelated picture for a diameter."""

from . import static_figures
from .angle_model import read_question

CONDITION = "aab6d4fd-29ab-4b85-9ce0-3bf072ab9106"
DETAIL = "2791f260-5ce1-4c3c-87b7-9bdc63ecbf10"


def settings(context):
    from ..triangles.isosceles.planner import _section

    condition = _section(context["normalized_content"], "condition")
    source = CONDITION if condition.get("asset_keys") else None
    model = read_question(condition["html"], source)
    # The reviewed drawings depict the obtuse angle only.
    illustrated = model.answer == 150
    return {model.mode: (CONDITION,) if illustrated else ()}, (
        {model.mode: (("detail", DETAIL),)} if illustrated else {}
    )


def selection(context):
    sources, details = settings(context)
    return static_figures.selection(context, read_question, sources, details, {})[2]


def prepare(context, generated):
    sources, details = settings(context)
    return static_figures.prepare(
        context, generated, read_question, sources, details, {}
    )
