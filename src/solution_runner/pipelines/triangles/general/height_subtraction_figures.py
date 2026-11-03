"""Keep the reviewed external-foot figure and remap its outlined letters."""

import gzip
import hashlib
from importlib.resources import files

from ...core.errors import ContentPlanError
from ...probability.solution_diagrams import spec
from ..isosceles.side_altitude_figures import _identity, condition_changes
from .angle_sources import reviewed_condition
from .height_subtraction_model import read_question
from .simple_angle_figures import _remapped

SOURCE = "a1ea1011-33a4-40e6-9512-dcd0909c8cb4"
KEYS = {SOURCE: "height_subtraction_condition"}
_HASHES = {SOURCE: "1003b945d12a6bbc4565c64266aa408f8ea52d941c5fd8e7453d20c6fe67097c"}


def source_bytes(source):
    if source not in _HASHES:
        raise ContentPlanError(
            "the height/subtraction image needs a mathematical audit"
        )
    raw = gzip.decompress(
        files(__package__).joinpath("assets/" + source + ".svgz").read_bytes()
    )
    if hashlib.sha256(raw).hexdigest() != _HASHES[source]:
        raise ContentPlanError("the audited height/subtraction SVG changed")
    return raw


def selection(context):
    asset, condition, source, raw, html = reviewed_condition(
        context, KEYS, source_bytes
    )
    model = read_question(html, asset["asset_id"])
    if model.frame != "ABC":
        diagram = spec(KEYS[source], _remapped(model, raw, "ABCH"))
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
