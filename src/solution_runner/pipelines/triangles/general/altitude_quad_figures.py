"""Keep compatible internal altitude figures and build the reviewed external branch."""

import gzip
import hashlib
from importlib.resources import files

from ...core.errors import ContentPlanError
from ...probability.solution_diagrams import spec
from ..isosceles.side_altitude_figures import _identity, condition_changes
from .altitude_quad_model import read_question
from .altitude_quad_svg import external_svg
from .angle_sources import reviewed_condition
from .simple_angle_figures import _remapped

ACUTE = "3c6d2a44-861f-4dbe-b088-436dd5451b81"
OTHER = "4dad3a58-bfe7-4b89-9a76-9136098b114b"
KEYS = {ACUTE: "altitude_quad_acute_condition", OTHER: "altitude_quad_other_condition"}
_HASHES = {
    ACUTE: "582f7b95e24e1af635915c3ea917db56d6ec19fb9f0a09df383c030f4bec1e11",
    OTHER: "1fac04927a0b58e3fad2d01d218427766c7c75defa45ec6464b06cfe3c95df25",
}


def source_bytes(source):
    if source not in _HASHES:
        raise ContentPlanError(
            "the altitude quadrilateral image needs a mathematical audit"
        )
    raw = gzip.decompress(
        files(__package__).joinpath("assets/" + source + ".svgz").read_bytes()
    )
    if hashlib.sha256(raw).hexdigest() != _HASHES[source]:
        raise ContentPlanError("the audited altitude quadrilateral SVG changed")
    return raw


def selection(context):
    asset, condition, source, raw, html = reviewed_condition(
        context, KEYS, source_bytes
    )
    model = read_question(html, asset["asset_id"])
    if model.alpha > 90:
        diagram = spec(KEYS[source], external_svg(model, raw))
    elif model.frame != "ABC":
        diagram = spec(KEYS[source], _remapped(model, raw, "ABCDEO"))
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
