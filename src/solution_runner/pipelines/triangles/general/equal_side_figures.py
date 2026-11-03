"""Keep compatible equal-side figures and use the shared outlined-letter remapper."""

import gzip
import hashlib
from importlib.resources import files

from ...core.errors import ContentPlanError
from ...probability.solution_diagrams import spec
from ..isosceles.side_altitude_figures import _identity, condition_changes
from .angle_sources import reviewed_condition
from .equal_side_model import read_question
from .exterior_bisector_svg import exterior_svg
from .simple_angle_figures import _remapped

EXTENSION = "2e9951a8-0515-442e-a55d-4cd9f3c803f7"
CONGRUENT = "cf3bda48-a265-42a2-b690-1f890d0d1566"
EXTERIOR = "ac8920ea-6ec7-4a2d-a861-708f43a3ba02"
SOURCES = {"extension": EXTENSION, "congruent": CONGRUENT, "exterior": EXTERIOR}
KEYS = {
    EXTENSION: "equal_side_extension_condition",
    CONGRUENT: "equal_side_congruent_condition",
    EXTERIOR: "equal_side_exterior_condition",
}
_HASHES = {
    EXTENSION: "57d576845bd1458e7a0e090c24b628f89f4355b7a141de743d45f1c09f0469ae",
    CONGRUENT: "669bf9990030cf20015ccbe5039cbaaff365f684348ebd7bd1ab6e5c13dc57ed",
    EXTERIOR: "b5ba4bf8e21160602f0a0144b59ddacb7b734cdd72eee7c02f22718216337a88",
}


def source_bytes(source):
    if source not in _HASHES:
        raise ContentPlanError("the equal-side image needs a mathematical audit")
    raw = gzip.decompress(
        files(__package__).joinpath("assets/" + source + ".svgz").read_bytes()
    )
    if hashlib.sha256(raw).hexdigest() != _HASHES[source]:
        raise ContentPlanError("the audited equal-side SVG changed")
    return raw


def selection(context):
    asset, condition, source, raw, html = reviewed_condition(
        context, KEYS, source_bytes
    )
    model = read_question(html, asset["asset_id"])
    if source != SOURCES[model.mode]:
        raise ContentPlanError(
            "the source diagram depicts a different equal-side construction"
        )
    if model.mode == "exterior" and model.alpha > model.beta:
        diagram = spec(KEYS[source], exterior_svg(model, raw))
    elif model.frame != "ABC":
        diagram = spec(
            KEYS[source],
            _remapped(model, raw, "ABDC" if model.mode == "extension" else "ABCDE"),
        )
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
