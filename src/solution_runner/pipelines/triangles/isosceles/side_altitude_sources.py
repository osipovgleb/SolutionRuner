"""Select audited native drawings by their actual roles and exact foot topology."""

import gzip
import hashlib
from importlib.resources import files

from ...core.errors import ContentPlanError

# digest, altitude vertex, other base vertex, apex, K construction, topology, crop
SOURCES = {
    "7882a0e2-3730-4c5a-954d-99b65a800a37": (
        "da8f3f06fa214ef1f175040f09db6e97b6caca4ff2323d306251b9fce99e3dfb",
        "A",
        "B",
        "C",
        False,
        1,
        True,
    ),
    "6e05b336-1a9d-4f77-ba24-a2d619fd02f5": (
        "93c105599f1c0ee500ecfa7b1f2b9fc64ead91dbcce93a82f3604477e3dc7861",
        "C",
        "A",
        "B",
        False,
        1,
        True,
    ),
    "9f99e601-0a60-47e7-a20e-934fda25122c": (
        "96b6c877c1ecfc93757dec088483b1764c9b2cfc6728959ab4f068a496bdc4d5",
        "A",
        "B",
        "C",
        False,
        1,
        True,
    ),
    "bd30b749-da28-45cf-8ae8-a4b19cd55fe0": (
        "bfffcabfe27fca78ebbe08e2b232c8aa82f2e06dfbcca34cc5bb75d9417d8950",
        "A",
        "B",
        "C",
        False,
        -1,
        False,
    ),
    "e646ef3d-a79c-4f92-a916-1e4b976041ca": (
        "428dfab16593c19f3ac245a1d9a0239a06d347a773be4af088619b202e0c9540",
        "A",
        "B",
        "C",
        False,
        -1,
        True,
    ),
    "cb4edfb8-827e-4028-b562-55a1fb4db07c": (
        "00c76d2093f590d18db6c7a082e938e8edc648bed35d4bb7dcd14715d345c469",
        "C",
        "A",
        "B",
        False,
        1,
        True,
    ),
    "2446836d-641d-400e-b4c3-fa09cf977dc3": (
        "2db2175d6b29448cdd9fa88476df5b85e52952aee0a8c9132b08511175730faa",
        "A",
        "B",
        "C",
        False,
        -1,
        False,
    ),
    "a41c52d0-9fcc-49cc-ace2-65c676d74aaf": (
        "575972a32c952064185bf37971e6c9bbfaf8f1173ade2910f5bdae2a57cdddb2",
        "A",
        "B",
        "C",
        True,
        -1,
        True,
    ),
    "e4647c04-5060-43c8-a3da-5958850c042f": (
        "bc5697224fdb174f79f96dff218d4ddbfc0e14c36e7b8a72de8f1e5805ee29ed",
        "A",
        "B",
        "C",
        True,
        1,
        False,
    ),
    "cb42a1f2-647b-46d4-8694-ef6fa14a4cdf": (
        "3cbe152ea57feb1f32ef207b873fb7385489cde655427cc77972be3889d76922",
        "A",
        "B",
        "C",
        True,
        1,
        False,
    ),
    "45a6fa73-fe2e-4355-8184-d09a848a9e82": (
        "ab4de6770b9af3ce325a20aa6092fe0b24436610382b2b5fd04329af7604801a",
        "A",
        "B",
        "C",
        False,
        1,
        True,
    ),
}
ZERO_KEY = "side_altitude_zero"
FONT_SOURCE = "a41c52d0-9fcc-49cc-ace2-65c676d74aaf"
NOTE_SOURCE = "cb42a1f2-647b-46d4-8694-ef6fa14a4cdf"
_KEYS = {"side_altitude_" + source[:8]: source for source in SOURCES}


def source_bytes(source):
    if source not in SOURCES:
        raise ContentPlanError("the side-altitude SVG needs a mathematical audit")
    raw = gzip.decompress(
        files(__package__).joinpath("assets/" + source + ".svgz").read_bytes()
    )
    if hashlib.sha256(raw).hexdigest() != SOURCES[source][0]:
        raise ContentPlanError("the audited side-altitude source changed")
    return raw


def seed(asset):
    key = asset.get("asset_key")
    if key == "image_1" and asset.get("asset_id") in SOURCES:
        return asset["asset_id"]
    if key == ZERO_KEY:
        return FONT_SOURCE
    if key in _KEYS:
        return _KEYS[key]
    raise ContentPlanError("the primary side-altitude figure is not reviewed")


def generated_key(source):
    return "side_altitude_" + source[:8]


def generated_keys():
    return {ZERO_KEY, *_KEYS}


def choose(model, current):
    with_k = model.given_kind == "side"
    expected = (
        model.vertex,
        model.other_base_vertex,
        model.apex,
        with_k,
        model.topology,
    )
    if model.topology == 0:
        return "zero", FONT_SOURCE
    if SOURCES[current][1:6] == expected and not SOURCES[current][6]:
        return "native", current
    compatible = [s for s, v in SOURCES.items() if v[1:6] == expected]
    uncropped = [s for s in compatible if not SOURCES[s][6]]
    if uncropped:
        return "native", uncropped[0]
    if current in compatible:
        return "crop", current
    if compatible:
        return "crop", compatible[0]
    # A reviewed canonical frame can be relabelled without changing its geometry.
    canonical = ("A", "B", "C", with_k, model.topology)
    candidates = [s for s, v in SOURCES.items() if v[1:6] == canonical]
    if not candidates:
        raise ContentPlanError(
            "no audited side-altitude drawing supports this topology"
        )
    source = next((s for s in candidates if not SOURCES[s][6]), candidates[0])
    return "remap", source
