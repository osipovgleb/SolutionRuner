"""Reuse exact section diagrams and move legacy condition pictures to the solution."""

from functools import partial

from bs4 import BeautifulSoup

from ..core.errors import ContentPlanError
from ..probability.solution_diagrams import spec
from ..quadrilaterals.parallelogram.midpoint_figures import _attach
from ..quadrilaterals.quantity_content import read_content
from ..triangles.isosceles.planner import _section
from ..triangles.isosceles.side_altitude_figures import _identity
from ..triangles.right.basic_parent import _targeted
from ..word_problems.common import rewrite
from .box_section_model import read_question
from .box_section_sources import FIGURES, PARENTS, source_bytes
from .box_section_svg import figure_svg

KEY = "box_section_solution"


def selection(context, *, rule):
    content, assets, owners = read_content(context, {"image_1", "image_2", KEY})
    condition = _section(content, "condition")
    if condition is None:
        raise ContentPlanError("one complete box section condition is required")
    soup = BeautifulSoup(condition["html"], "html.parser")
    images = soup.find_all("img")
    if len(images) > 1 or len(assets) > 1:
        raise ContentPlanError("one reviewed section diagram is supported")
    source = images[0].get("data-asset-id") if images else None
    m = read_question(condition["html"], source)
    old = next(iter(assets.values()), None)
    if old:
        if old["asset_key"] in {"image_1", "image_2"}:
            source_bytes(old["asset_id"])
        if old["asset_key"] != "image_1" and owners[old["asset_key"]] != "solution":
            raise ContentPlanError("generated section diagrams belong in the solution")
    base = PARENTS[rule][0]
    candidates = (
        ([old["asset_id"]] if old and old["asset_id"] in FIGURES else [])
        + [base]
        + list(FIGURES)
    )
    source = next(
        (s for s in candidates if FIGURES[s] == tuple(sorted(m.vertices))), None
    )
    drawing = None if source else spec(KEY, figure_svg(m, base))
    return m, condition, old, owners, source or base, drawing


def diagram_specs(context, *, rule):
    drawing = selection(context, rule=rule)[-1]
    return (drawing,) if drawing else ()


vertical_specs = partial(diagram_specs, rule="solid-box-vertical-section")
oblique_specs = partial(diagram_specs, rule="solid-box-oblique-section")


def prepare(context, generated, *, rule):
    m, condition, old, owners, source, drawing = selection(context, rule=rule)
    if len(generated) != bool(drawing):
        raise ContentPlanError("the prepared box section differs from the actual plane")
    key = (
        KEY
        if drawing
        else "image_2"
        if old
        and (old["asset_key"] == "image_2" or owners[old["asset_key"]] == "condition")
        else "image_1"
    )
    identifier, url = _identity(key, source, drawing, generated)
    picture, changes = _attach(old, key, identifier, url, "solution")
    soup = BeautifulSoup(condition["html"], "html.parser")
    if soup.find("img"):
        soup.img.decompose()
        change = rewrite(
            _targeted(condition),
            "condition",
            condition.get("title", "Условие"),
            str(soup),
        )
        change["value"]["asset_keys"] = []
        changes.append(change)
    return m, tuple(changes), picture, (key,)
