"""Reviewed unnumbered source diagrams, their geometry and parent methods."""

import gzip
import hashlib
from importlib.resources import files

from ...core.errors import ContentPlanError
from .midpoint_model import HEIGHT, TWO_TRAPEZOID, TWO_TRIANGLE, VARIGNON

TRAPEZOID_HEIGHT = "026445da-c5cc-421d-9617-99a9526428a5"
TRAPEZOID_MEDIAN = "66e2ea05-1d95-4964-8611-efc5342d8806"
VARIGNON_FIGURE = "ccc9565b-f51d-483b-8f52-550bae30a7db"
TRIANGLE_HEIGHT = "40db11b0-156b-414f-a046-ca6e41b37516"
HEIGHT_CONDITION = "f751e689-ec08-4bc6-9de7-d55c46285ba8"
# Each frame maps the canonical mathematical roles to actual source lettering.
SOURCES = {
    TRAPEZOID_HEIGHT: ("trapezoid", "ABCD", "height", "ABDCEh"),
    TRAPEZOID_MEDIAN: ("trapezoid", "ABCD", "median", "ABDCE"),
    "4ecd1f86-80ad-4742-9661-949724aeaac1": ("trapezoid", "BCDA", "height", "ABDCEh"),
    "17166b67-74e2-4ed6-8e78-201cc0d2152f": ("trapezoid", "DABC", "height", "ABDCEh"),
    "7ea4264e-b440-4b12-b08a-c76ae6052b94": ("trapezoid", "DABC", "median", "ABDCE"),
    VARIGNON_FIGURE: (
        "varignon",
        "ABCD",
        "varignon",
        ("A", "B", "D", "C", "A'", "B'", "C'", "D'"),
    ),
    TRIANGLE_HEIGHT: ("triangle", "ABCD", "height", "ABCDEH"),
    "313e1a07-bef2-45c4-ab67-409bc153050f": ("triangle", "BCDA", "height", "ABCDEH"),
    "b084d4ab-37d1-48f6-87f7-98875970f979": ("triangle", "BCDA", "condition", "ABCDE"),
    HEIGHT_CONDITION: ("trapezoid", "DCBA", "condition", "ABCDE"),
}
PARENTS = {
    TWO_TRAPEZOID: (
        TRAPEZOID_HEIGHT,
        (TRAPEZOID_HEIGHT, TRAPEZOID_MEDIAN),
        "15f2a14ba8c5e212fd1f7f986a57d556d8b72cc474a68f0213afcc63441c2b99",
    ),
    VARIGNON: (
        VARIGNON_FIGURE,
        (VARIGNON_FIGURE,),
        "78f8bb5bcc90658105a717aa48c23d737fc836efe8287be92807ef0c444206a5",
    ),
    TWO_TRIANGLE: (
        TRIANGLE_HEIGHT,
        (TRIANGLE_HEIGHT,),
        "c03ffc94898f1284fff63f91410c5ca724ff7358315859c5ccc5eb424263d528",
    ),
    HEIGHT: (
        HEIGHT_CONDITION,
        (),
        "a7f5e9a1a3a4e6755a29e3b8f910c96cb02eae76eb224be0b6a8cd5fbd9f96e2",
    ),
}

_HASHES = {
    "026445da-c5cc-421d-9617-99a9526428a5": "72961d0ea2767f534b601d6c7b414500a037ea8ff8b4cb94920f323a666863c7",
    "17166b67-74e2-4ed6-8e78-201cc0d2152f": "87f407727f29399c2e61bc2849088c50a0ac9841176694038283ddb702fd8c02",
    "313e1a07-bef2-45c4-ab67-409bc153050f": "104c69a59ea3a22a9a123f63c8407ac989783a80b544b6b2ede5b5905541aa88",
    "40db11b0-156b-414f-a046-ca6e41b37516": "8400d4e18910834f252bfaa0784e45c628ec9765ca9beded3fa6e435af07eefc",
    "4ecd1f86-80ad-4742-9661-949724aeaac1": "8483e19b9d3ff232ef5f1c72d01f3823540e4633c9d1a51c85e9b1aaf5f0dc5e",
    "66e2ea05-1d95-4964-8611-efc5342d8806": "95e985b32383f85e08b8579d4c77b2bfe5da8c6fb085f2d59603afe86da8149a",
    "7ea4264e-b440-4b12-b08a-c76ae6052b94": "bbe928f0fcf4a9d211f06f9aa0120fe8792539d3e03cb0e587388440d0957ad8",
    "b084d4ab-37d1-48f6-87f7-98875970f979": "86d0877fad4e3a93cdae12792b0378c23c827f818ec4e51e9c34a8f18090c3a6",
    "ccc9565b-f51d-483b-8f52-550bae30a7db": "bb3d95d8534736618f2d7d5c8e85afc196e49c93bb664d733d63255cce8a507e",
    "f751e689-ec08-4bc6-9de7-d55c46285ba8": "b4187dfc25282363e46482e0c12a0c108db76018f936517ee7e300d3ad0b7a47",
}


def source_bytes(identifier):
    if identifier not in SOURCES:
        raise ContentPlanError("the midpoint figure needs a mathematical audit")
    raw = gzip.decompress(
        files(__package__).joinpath("assets/" + identifier + ".svgz").read_bytes()
    )
    if hashlib.sha256(raw).hexdigest() != _HASHES[identifier]:
        raise ContentPlanError("the reviewed midpoint SVG changed")
    return raw


def review_parent(rule, identifier, html, assets):
    if rule not in PARENTS:
        raise ContentPlanError("unreviewed midpoint parent method")
    primary, figures, digest = PARENTS[rule]
    if (
        identifier != primary
        or not isinstance(html, str)
        or hashlib.sha256(html.encode()).hexdigest() != digest
    ):
        raise ContentPlanError("the reviewed midpoint parent method changed")
    expected = [("image_" + str(i + 1), source) for i, source in enumerate(figures)]
    if not isinstance(assets, (list, tuple)) or any(
        not isinstance(a, dict) for a in assets
    ):
        raise ContentPlanError("the parent midpoint figures must be complete")
    if [
        (a.get("asset_key"), a.get("source_asset_id")) for a in assets
    ] != expected or any(
        a.get("url") != "/assets/" + a["source_asset_id"] for a in assets
    ):
        raise ContentPlanError("the reviewed parent midpoint figures changed")
    for source in (primary, *figures):
        source_bytes(source)
