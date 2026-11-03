"""Select audited angle diagrams by vertex roles, construction and topology."""

import gzip
import hashlib
from importlib.resources import files

import sympy as sp
from bs4 import BeautifulSoup

from ...core.errors import ContentPlanError
from ...probability.solution_diagrams import spec
from .altitude_angle_svg import altitude_svg
from .angle_model import read_question
from .angle_svg import exterior_svg
from .area_figures import ACUTE, NARROW, OBTUSE, plain_triangle_svg
from .area_figures import source_bytes as area_source_bytes
from .basic_figures import uncrop_svg
from .planner import _section
from .side_altitude_figures import _identity, condition_changes

EXTERIOR_BASE = "89190033-7852-419f-9161-8ce7f5c369fb"
EXTERIOR_GIVEN = "a7eed42f-2d29-485b-967e-3bb02c95b67c"
EXTERIOR_VERTEX = "158dae5e-720d-40cb-8a48-169bfb01c141"
LARGER = "0b17fb29-6d2a-4a25-bb98-225021087bef"
DIFFERENCE = "8fc51584-29f8-4227-8d92-7a8081892eb9"
ALTITUDE = "b1d8b726-29ef-4d29-80b9-eba3cdd92cf2"
KEY = "isosceles_angle_condition"
_HASHES = {
    ALTITUDE: "a03dbfe0924b1b4b778f9a54edeb73912475f185d61dd052366b912956a3329c",
    EXTERIOR_BASE: "164086954ed0a7c6d2ffa035eaa91b382786a5a85fd946594d5b35c8beeeeae0",
    EXTERIOR_GIVEN: "465f22c20400f14f5c2b25e0077ef9e62a8140ad85d144712a50f1b84c7e7c55",
    EXTERIOR_VERTEX: "e0a0bd671f6af6f40bb24ff228148bef8db51175c167c66e8e34e870cdc16150",
    LARGER: "e3b0ad2fe929d6e1dc0a2d4663509eb196edd2c364e3b1cb7c399882ad10475d",
    DIFFERENCE: "209cda0bd002afc7f8245bb1c9a1c656de4010ca1fd210e5067543d60b80bc5a",
}


def source_bytes(source):
    if source in {ACUTE, NARROW, OBTUSE}:
        return area_source_bytes(source)
    if source not in _HASHES:
        raise ContentPlanError("the angle diagram source needs review")
    raw = gzip.decompress(
        files(__package__).joinpath("assets/" + source + ".svgz").read_bytes()
    )
    if hashlib.sha256(raw).hexdigest() != _HASHES[source]:
        raise ContentPlanError("the audited angle diagram changed")
    return raw


def _drawing(model, current):
    if model.given_kind == "altitude":
        raw = source_bytes(ALTITUDE)
        if model.apex == "C" and model.altitude_vertex == "A" and model.topology == 1:
            return "image_1", ALTITUDE, None
        return KEY, ALTITUDE, spec(KEY, altitude_svg(model, raw))
    if model.requested_kind == "external_base" or model.given_kind.startswith(
        "external_"
    ):
        vertex = model.given_kind == "external_vertex"
        source = (
            EXTERIOR_VERTEX
            if vertex
            else EXTERIOR_GIVEN
            if model.given_kind == "external_base"
            else EXTERIOR_BASE
        )
        raw = source_bytes(source)
        center = (
            model.given_vertex
            if model.given_kind == "external_base"
            else model.requested[1]
            if not vertex
            else model.apex
        )
        compatible = model.topology == 1 and (
            (vertex and model.apex == "B" and model.requested == "C")
            or (not vertex and model.apex == "C" and center == "B")
        )
        if compatible:
            return (
                (KEY, source, spec(KEY, uncrop_svg(raw)))
                if source == EXTERIOR_BASE
                else ("image_1", source, None)
            )
        return KEY, source, spec(KEY, exterior_svg(model, raw, vertex))
    if model.apex != "C" or model.topology == 0:
        ratio = 1 / (2 * sp.tan(sp.pi * model.apex_angle / 360))
        return KEY, ACUTE, spec(KEY, plain_triangle_svg(model.apex, ratio))
    compatible = (
        {ACUTE, NARROW, LARGER} if model.topology == 1 else {OBTUSE, DIFFERENCE}
    )
    source = current.get("asset_id")
    if current.get("asset_key") != "image_1" or source not in compatible:
        source = ACUTE if model.topology == 1 else OBTUSE
    source_bytes(source)
    return "image_1", source, None


def selection(context):
    content = context.get("normalized_content")
    if (
        not isinstance(content, dict)
        or content.get("schema_version") != 3
        or content.get("format") != "teacherhelper-normalized"
    ):
        raise ContentPlanError("schema-v3 normalized angle content is required")
    assets = content.get("assets")
    if (
        not isinstance(assets, list)
        or len(assets) != 1
        or not isinstance(assets[0], dict)
    ):
        raise ContentPlanError("one audited angle condition asset is required")
    current = assets[0]
    key = current.get("asset_key")
    identifier = current.get("asset_id")
    if (
        key not in {"image_1", KEY}
        or not isinstance(identifier, str)
        or not identifier
        or current.get("kind") != "ordinary_image"
        or current.get("url") != "/assets/" + identifier
    ):
        raise ContentPlanError("the angle diagram metadata changed")
    if key == "image_1":
        source_bytes(identifier)
    condition = _section(content, "condition")
    if condition is None or not isinstance(condition.get("html"), str):
        raise ContentPlanError("one complete angle condition is required")
    soup = BeautifulSoup(condition["html"], "html.parser")
    images = soup.find_all("img")
    if (
        len(images) != 1
        or images[0].get("data-asset-key") != key
        or images[0].get("data-asset-id") != identifier
    ):
        raise ContentPlanError("the angle condition figure differs from its metadata")
    images[0]["data-asset-key"] = "image_1"
    model = read_question(str(soup), identifier)
    return model, current, condition, *_drawing(model, current)


def diagram_specs(context):
    diagram = selection(context)[-1]
    return (diagram,) if diagram else ()


def prepare(context, generated):
    model, current, condition, key, source, diagram = selection(context)
    identifier, url = _identity(key, source, diagram, generated)
    return model, condition_changes(context, condition, current, key, identifier, url)
