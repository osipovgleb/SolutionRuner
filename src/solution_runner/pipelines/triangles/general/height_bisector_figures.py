"""Keep compatible internal height/bisector figures and build the reviewed external branch."""

import gzip
import hashlib
from importlib.resources import files

from ...core.errors import ContentPlanError
from ...probability.solution_diagrams import spec
from ..isosceles.side_altitude_figures import _identity, condition_changes
from .angle_sources import reviewed_condition
from .height_bisector_model import read_question
from .height_bisector_svg import external_svg
from .simple_angle_figures import _remapped

SOURCE = "04b1854c-9a0b-4b63-8ddb-a45317e32978"
KEYS = {SOURCE: "height_bisector_condition"}
_HASHES = {SOURCE: "b6f6f3360efb812685eba06797018d5d5855dc646968783257b702f191a4366a"}


def source_bytes(source):
    if source not in _HASHES:
        raise ContentPlanError("the height/bisector image needs a mathematical audit")
    raw = gzip.decompress(
        files(__package__).joinpath("assets/" + source + ".svgz").read_bytes()
    )
    if hashlib.sha256(raw).hexdigest() != _HASHES[source]:
        raise ContentPlanError("the audited height/bisector SVG changed")
    return raw


def selection(context):
    asset, condition, source, raw, html = reviewed_condition(
        context, KEYS, source_bytes
    )
    model = read_question(html, asset["asset_id"])
    if model.theta > 45:
        diagram = spec(KEYS[source], external_svg(model, raw))
    elif model.frame != "ABC":
        diagram = spec(KEYS[source], _remapped(model, raw, "ABCDOH"))
    else:
        diagram = None
    return model, asset, condition, source, diagram


def diagram_specs(context):
    diagram = selection(context)[-1]
    return (diagram,) if diagram else ()


def prepare(context, generated):
    model, asset, condition, source, diagram = selection(context)
    key = diagram["asset_key"] if diagram else "image_1"
    identifier, url = _identity(key, source, diagram, generated)
    return model, condition_changes(context, condition, asset, key, identifier, url)
