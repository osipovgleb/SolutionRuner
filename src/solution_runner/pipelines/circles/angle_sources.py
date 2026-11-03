"""Pinned complete parent methods and audited original circle SVG aliases."""

import gzip
import hashlib
from importlib.resources import files

from ..core.errors import ContentPlanError

PARENTS = {
    "circle-central-angle-difference": (
        "515f640e-4cd6-40ee-94b4-d171ac58f6ad",
        (("image_1", "515f640e-4cd6-40ee-94b4-d171ac58f6ad"),),
        "7e4c4a84dbc180a8dc867b566e837c8b37c67ca55ef5f0821bc39f421a9ba29d",
    ),
    "circle-inscribed-angle-difference": (
        "e37b7d86-ef1d-473b-8ef1-2777aefff55d",
        (),
        "4273da01981f4c6ba69a1224f2ca1ae519bbb4154188f232b8d3d57dc0bad0d2",
    ),
    "circle-inscribed-angle-arc-fraction": (
        "40ccd98b-48c9-469c-b30c-bbd010257d7c",
        (),
        "3bb5c1618d16a3bea8312f495f621d1fe7c3db1ad424a95a9d2f9284db229c74",
    ),
    "circle-inscribed-angle-two-arcs": (
        "d98c679b-1fdf-4382-9fad-5c11e6512d0f",
        (),
        "0491450e39d6ac38089942026fbd35156c2a07c3de2221b80f628f09d808564c",
    ),
    "circle-diameters-inscribed-to-central": (
        "1f80d796-67fd-4b3b-9edc-e038caf927ee",
        (),
        "fe6934735ffe1aa62bbbaa9721850f388480b504e80e5ce3678a4153a8bbcc6f",
    ),
    "circle-diameters-central-to-inscribed": (
        "1f80d796-67fd-4b3b-9edc-e038caf927ee",
        (),
        "45b78f9a3afe133eb860f433143761d597c879f443821363836670720cd5ae5d",
    ),
    "circle-secant-angle-arc-difference": (
        "f98a097b-c129-44ea-b49b-059bde4c8963",
        (),
        "fce3960501562b7a4234272edcab7925a8959230844f88c274919a9e0f92f9cc",
    ),
}

SOURCES = {
    "1f80d796-67fd-4b3b-9edc-e038caf927ee": (
        "1f80d796-67fd-4b3b-9edc-e038caf927ee",
        "d7de5d0df467f351ddd562bee5dc6b24727db426f42f8ea40b783936f3be5e61",
    ),
    "3a014817-745a-4049-8437-07d8337f8f20": (
        "3a014817-745a-4049-8437-07d8337f8f20",
        "c35ec6c4c6f2e1c741bec47524bf6edc6a2aca49668ca02665bb2f7e91790729",
    ),
    "40ccd98b-48c9-469c-b30c-bbd010257d7c": (
        "40ccd98b-48c9-469c-b30c-bbd010257d7c",
        "1e1e1273e8640d69bee3355ffa5a4bf3a2ea37bd830d4f8f3514cf3c38f3cd21",
    ),
    "45075378-fe37-4226-87bf-d90d9275317e": (
        "45075378-fe37-4226-87bf-d90d9275317e",
        "da09a494eac19901edf1f663a6c3fdb4e63493114b2aaf290ebafb3b91cc85f8",
    ),
    "515f640e-4cd6-40ee-94b4-d171ac58f6ad": (
        "515f640e-4cd6-40ee-94b4-d171ac58f6ad",
        "8bc55c1fb21e9deb925a5a21bb849fe2df6515d24dd92177c115dd9c0ee0dbcd",
    ),
    "5be3c78f-0682-4cce-a623-1e7ff255692c": (
        "1f80d796-67fd-4b3b-9edc-e038caf927ee",
        "d7de5d0df467f351ddd562bee5dc6b24727db426f42f8ea40b783936f3be5e61",
    ),
    "8aee4b45-3b33-4f1b-b6c3-236cf0eeb1f1": (
        "8aee4b45-3b33-4f1b-b6c3-236cf0eeb1f1",
        "1070993890807a48c6085ed0b945078d7450656d209bd4f66521bd91a90bfedc",
    ),
    "d98c679b-1fdf-4382-9fad-5c11e6512d0f": (
        "d98c679b-1fdf-4382-9fad-5c11e6512d0f",
        "a794f19bcdff114f3817368cfbda8626d938cef8a96cd8e4386ca811ddaf13d2",
    ),
    "e37b7d86-ef1d-473b-8ef1-2777aefff55d": (
        "e37b7d86-ef1d-473b-8ef1-2777aefff55d",
        "7fc9937004a20f86de08bf32fed05f078eda44425bf42c855c99a36dbb7283ab",
    ),
    "e5fc5324-bed5-42ef-a335-d244924dfe9a": (
        "e5fc5324-bed5-42ef-a335-d244924dfe9a",
        "f6703ed7641df92842f2eadc63bd4fd1cfa423d4cce4dd16f8f336427a3d0969",
    ),
    "f98a097b-c129-44ea-b49b-059bde4c8963": (
        "f98a097b-c129-44ea-b49b-059bde4c8963",
        "927bfbd86a3240c54661c4d598584ce8fddc71d01ccf574a059f6fcdd67f50c9",
    ),
}


def source_bytes(source):
    if source not in SOURCES:
        raise ContentPlanError("the circle-angle source needs a review")
    canonical, digest = SOURCES[source]
    raw = gzip.decompress(
        files(__package__).joinpath("assets/" + canonical + ".svgz").read_bytes()
    )
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ContentPlanError("the reviewed circle-angle SVG changed")
    return raw


def review_parent(rule, primary, html, assets):
    if rule not in PARENTS:
        raise ContentPlanError("an explicit reviewed circle-angle rule is required")
    expected, figures, digest = PARENTS[rule]
    if (
        primary != expected
        or not isinstance(html, str)
        or hashlib.sha256(html.encode()).hexdigest() != digest
    ):
        raise ContentPlanError("the complete reviewed circle-angle parent changed")
    if not isinstance(assets, (tuple, list)) or any(
        not isinstance(a, dict) for a in assets
    ):
        raise ContentPlanError(
            "complete circle-angle parent asset metadata is required"
        )
    if [(a.get("asset_key"), a.get("source_asset_id")) for a in assets] != list(
        figures
    ) or any(a.get("url") != "/assets/" + a["source_asset_id"] for a in assets):
        raise ContentPlanError("the reviewed circle-angle solution figures changed")
    for source in (primary, *(s for _, s in figures)):
        source_bytes(source)
