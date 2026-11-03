"""Audited height and rhombus diagrams and the complete parent methods."""

import gzip
import hashlib
from importlib.resources import files

from ...core.errors import ContentPlanError

PARENTS = {
    "rhombus-side-sixty-height": (
        "0f9596a2-7160-4a52-8155-cdecf3de5824",
        (),
        "5483e1d77cb4cb86db2833f1d44a39d2379ef9c7c1f70ce6fa7adefade335b5f",
    ),
    "rhombus-side-sixty-long-diagonal": (
        "d079942f-59e2-4f99-8e45-e295851aa7c1",
        (),
        "0cc0defac8151589979f0ff7c9773334b53750dcbf89f3e81175434f362a0314",
    ),
    "rhombus-diagonal-ratio-perimeter-height": (
        "fc78faa7-5ccc-40bd-8519-e9d4a1629853",
        (),
        "31b84cf0425348aeff727e9df02fd0892a54bdbf3f6ac6a01390243fb33d102b",
    ),
    "parallelogram-sine-greater-height": (
        "19b90e5e-1140-484f-8100-ead74bd010e9",
        (),
        "4baca198f4e03f627b4bf7391dbd1f09991b1a02c15a1d13f5e9e772fee6f15f",
    ),
    "parallelogram-base-height-transfer": (
        "c45d5a90-41dd-4849-8c26-9289880cecfb",
        (
            ("image_1", "c45d5a90-41dd-4849-8c26-9289880cecfb"),
            ("image_2", "f2ccbf6e-93b7-4dc0-96fa-ee00fe7aa8f2"),
        ),
        "70fc678933a4e3b602a38e7c8e1a7d133fd6e10f56f0743f7561c9ac67114e59",
    ),
    "parallelogram-area-greater-height": (
        "046e3609-22e3-41c4-be82-0f3022ce9151",
        (),
        "68e3a7a8b624288fecc3d5250b6117db01d1a457275b995932d765ceb3815def",
    ),
    "rhombus-height-thirty-area": (
        "0a581314-6063-4c87-95eb-073086a172f4",
        (),
        "07d0bd977bc99fe319c32287a4424ad1af86bab8d1fb0090eb4f59c840dde0ac",
    ),
    "rhombus-diagonals-area": (
        "0a581314-6063-4c87-95eb-073086a172f4",
        (),
        "9abeeef615e6368c8d39bd0f5fbb63e6c976e8bfb83d73865efda05749124f14",
    ),
    "rhombus-area-known-diagonal": (
        "0a581314-6063-4c87-95eb-073086a172f4",
        (),
        "4986bd825d23493c8f16171ff5e279c2877f708d3db07a29f34167e5f79c37f4",
    ),
    "rhombus-area-diagonal-factor-small": (
        "0a581314-6063-4c87-95eb-073086a172f4",
        (),
        "98f42c610d5bafd4dce82727d6bc38e238717902ca210eaf231878189556f3db",
    ),
}
_HASHES = {
    "0f9596a2-7160-4a52-8155-cdecf3de5824": "4fafbe2ecdc9be611509e252d7ed1b3e89b6f029502e7021d65cd49e4461bccf",
    "d079942f-59e2-4f99-8e45-e295851aa7c1": "ee9f58552447e8b7021268366be5ef8d33604b9cba86d45d60b7f924cd7c3cf0",
    "fc78faa7-5ccc-40bd-8519-e9d4a1629853": "1f784e9f14ddd615fef82b2ef54487dc6f2a1fe5a1d871bc57bae0ce8b87f67b",
    "046e3609-22e3-41c4-be82-0f3022ce9151": "36b533052f1bfa0c49842754c4d9de41ca06d2cad4729d3c26c4cc99620e54af",
    "19b90e5e-1140-484f-8100-ead74bd010e9": "ef05b6cd65fb79b9f301536c32f66e12b1175be1c674eda399a7fdab2f7cb341",
    "0a581314-6063-4c87-95eb-073086a172f4": "bdd8da0d7711b8559b962211bcafd9240105f6ce013bf9fca8535dc9fa63d9ca",
    "f2ccbf6e-93b7-4dc0-96fa-ee00fe7aa8f2": "94d371ab078af43f6bb278f25f749f0e57445011f3ec1cd3d5568225ff599d5f",
    "c45d5a90-41dd-4849-8c26-9289880cecfb": "27abb3ef12b56b2a49e89d44ac3df4cd1176592dafef938adf7cc267321045b9",
}


def source_bytes(source):
    if source not in _HASHES:
        raise ContentPlanError("the parallelogram quantity figure needs an audit")
    raw = gzip.decompress(
        files(__package__).joinpath("assets/" + source + ".svgz").read_bytes()
    )
    if hashlib.sha256(raw).hexdigest() != _HASHES[source]:
        raise ContentPlanError("the reviewed parallelogram quantity SVG changed")
    return raw


def review_parent(rule, primary, html, assets):
    if rule not in PARENTS:
        raise ContentPlanError("unreviewed parallelogram quantity method")
    expected, figures, digest = PARENTS[rule]
    if (
        primary != expected
        or not isinstance(html, str)
        or hashlib.sha256(html.encode()).hexdigest() != digest
    ):
        raise ContentPlanError("the reviewed parallelogram quantity parent changed")
    if not isinstance(assets, (tuple, list)) or any(
        not isinstance(a, dict) for a in assets
    ):
        raise ContentPlanError("complete parent figure metadata is required")
    if [(a.get("asset_key"), a.get("source_asset_id")) for a in assets] != list(
        figures
    ) or any(a.get("url") != "/assets/" + a["source_asset_id"] for a in assets):
        raise ContentPlanError("the reviewed parent quantity figures changed")
    for source in (primary, *(s for _, s in figures)):
        source_bytes(source)
