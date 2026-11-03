"""Reviewed compatible square and rectangle styles, with exact parent methods."""

import gzip
import hashlib
from importlib.resources import files

from ...core.errors import ContentPlanError

PARENTS = {
    "square-diagonal-area": (
        "fb7e41fd-a34d-4624-acdd-47fcd236aed9",
        "c3d11536748a9a230027f81794c5c09a7dfaa13ac018da758a07d260c9693306",
    ),
    "rectangle-area-difference-larger-side": (
        "4bcf7ae7-9b12-46c5-a529-fd562577dd45",
        "f1e514d4cf308896940c3db374cf0d1b0a29ad63ebc49dcf53d4d5adf49eee75",
    ),
    "rectangle-area-ratio-perimeter": (
        "4bcf7ae7-9b12-46c5-a529-fd562577dd45",
        "6e6691f6d5a712d15593776d7c52fc6d6fd9a762f6c291327e2e9a9b7b4feecf",
    ),
    "rectangle-perimeter-area-larger-side": (
        "4bcf7ae7-9b12-46c5-a529-fd562577dd45",
        "a72d8a6973c65a19340d35adaa556b82a07e4c15e22e8a88529dea34718dc09f",
    ),
    "rectangle-perimeter-diagonal-area": (
        "4989651b-d3a3-4011-bfe9-a8696260167b",
        "117c0caa98aba954fa4834f3c9176b491b981dcf9dab3ddbf6b2f29dfbc75624",
    ),
    "rectangle-perimeter-area-diagonal": (
        "848ff2dd-fce4-4a83-86a8-84bdaaabfe66",
        "45cff6e28d1bd89a2514988fb4be3aa23cd3812e59818023e8e5d6ea12b1625d",
    ),
}
_HASHES = {
    "4989651b-d3a3-4011-bfe9-a8696260167b": "9b27e6039c1574e1223e7bb8b4719ddce367b3e7440d3ebc0bd2fde34067a30a",
    "fb7e41fd-a34d-4624-acdd-47fcd236aed9": "f1d1df7c78aad7ad508764dce3e7da13f58185bb60828e6fd3c635901249f0ae",
    "4bcf7ae7-9b12-46c5-a529-fd562577dd45": "42e96f096776d5958233ef3bf69fe5e16c2ad547e56f880c30d5dbca11d2a3d2",
    "848ff2dd-fce4-4a83-86a8-84bdaaabfe66": "d301510305e59152fc2ecc95ed255f1085224090728a68588d36c0a11e313201",
}


def source_bytes(source):
    if source not in _HASHES:
        raise ContentPlanError("the rectangle figure needs a mathematical audit")
    raw = gzip.decompress(
        files(__package__).joinpath("assets/" + source + ".svgz").read_bytes()
    )
    if hashlib.sha256(raw).hexdigest() != _HASHES[source]:
        raise ContentPlanError("the reviewed rectangle SVG changed")
    return raw


def review_parent(rule, source, html, assets):
    if rule not in PARENTS:
        raise ContentPlanError("unreviewed square or rectangle parent method")
    expected, digest = PARENTS[rule]
    if (
        source != expected
        or not isinstance(html, str)
        or hashlib.sha256(html.encode()).hexdigest() != digest
        or not isinstance(assets, (tuple, list))
        or assets
    ):
        raise ContentPlanError("the reviewed rectangle parent method or figure changed")
    source_bytes(source)
