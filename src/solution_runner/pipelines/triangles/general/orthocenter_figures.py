"""Keep compatible orthocenter figures and draw external or coincident point roles."""

import gzip
import hashlib
from importlib.resources import files

from ...core.errors import ContentPlanError
from ...probability.solution_diagrams import spec
from ..isosceles.side_altitude_figures import _identity, condition_changes
from .angle_sources import reviewed_condition
from .orthocenter_model import read_question
from .orthocenter_svg import orthocenter_svg
from .simple_angle_figures import _remapped

SOURCE = "86889ade-4724-487b-b241-b45b40f5c3f5"
LINES_SOURCE = "e0a9ce9a-f9d4-4ab4-b09b-59e0487605da"
SOURCES = {"rays": SOURCE, "lines": LINES_SOURCE}
KEYS = {SOURCE: "orthocenter_condition", LINES_SOURCE: "altitude_lines_condition"}
_HASHES = {
    SOURCE: "607c561f959935b5e7636999c639b1b0d6c0f0b5cd680a0f819b862dbb807656",
    LINES_SOURCE: "73a3e9135d36c850c027a890424a39769d8b51348d87f5365552bfa508185551",
}


def source_bytes(source):
    if source not in _HASHES:
        raise ContentPlanError("the orthocenter image needs a mathematical audit")
    raw = gzip.decompress(
        files(__package__).joinpath("assets/" + source + ".svgz").read_bytes()
    )
    if hashlib.sha256(raw).hexdigest() != _HASHES[source]:
        raise ContentPlanError("the audited orthocenter SVG changed")
    return raw


def selection(context):
    asset, condition, source, raw, html = reviewed_condition(
        context, KEYS, source_bytes
    )
    model = read_question(html, asset["asset_id"])
    if source != SOURCES[model.mode]:
        raise ContentPlanError(
            "the source diagram depicts a different altitude question"
        )
    if max(model.alpha, model.beta, model.gamma) >= 90:
        diagram = spec(KEYS[source], orthocenter_svg(model, raw))
    elif model.frame != "ABC":
        diagram = spec(KEYS[source], _remapped(model, raw, "ABCDEFO"))
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
