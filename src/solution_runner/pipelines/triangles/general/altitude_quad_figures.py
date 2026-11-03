"""Keep compatible internal altitude figures and build the reviewed external branch."""

import gzip
import hashlib
from importlib.resources import files

from bs4 import BeautifulSoup

from ...core.errors import ContentPlanError
from ...probability.solution_diagrams import spec
from ..isosceles.planner import _section
from ..isosceles.side_altitude_figures import _identity, condition_changes
from .altitude_quad_model import read_question
from .altitude_quad_svg import external_svg
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
    content = context.get("normalized_content")
    if (
        not isinstance(content, dict)
        or content.get("schema_version") != 3
        or content.get("format") != "teacherhelper-normalized"
    ):
        raise ContentPlanError(
            "schema-v3 normalized altitude quadrilateral content is required"
        )
    assets = content.get("assets")
    if (
        not isinstance(assets, list)
        or len(assets) != 1
        or not isinstance(assets[0], dict)
    ):
        raise ContentPlanError(
            "one reviewed altitude quadrilateral condition figure is required"
        )
    asset = assets[0]
    key, identifier = asset.get("asset_key"), asset.get("asset_id")
    if (
        key not in {"image_1", *KEYS.values()}
        or not isinstance(identifier, str)
        or not identifier
        or asset.get("kind") != "ordinary_image"
        or asset.get("url") != "/assets/" + identifier
    ):
        raise ContentPlanError("the altitude quadrilateral image metadata changed")
    source = (
        identifier if key == "image_1" else next(s for s, k in KEYS.items() if k == key)
    )
    raw = source_bytes(source)
    condition = _section(content, "condition")
    if condition is None or not isinstance(condition.get("html"), str):
        raise ContentPlanError(
            "one complete altitude quadrilateral condition is required"
        )
    soup = BeautifulSoup(condition["html"], "html.parser")
    images = soup.find_all("img")
    if (
        len(images) != 1
        or images[0].get("data-asset-key") != key
        or images[0].get("data-asset-id") != identifier
    ):
        raise ContentPlanError(
            "the altitude quadrilateral image differs from its metadata"
        )
    images[0]["data-asset-key"] = "image_1"
    model = read_question(str(soup), identifier)
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
