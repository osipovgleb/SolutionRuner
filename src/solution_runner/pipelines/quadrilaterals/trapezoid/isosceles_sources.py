"""Audited parent methods and exact SVG aliases for isosceles trapezoids."""

import gzip
import hashlib
from importlib.resources import files

from ...core.errors import ContentPlanError

PARENTS = {
    "isosceles-trapezoid-bases-leg-sine": (
        "42c396d3-3418-40f8-b80e-1eb6102702a1",
        (),
        "8afc8dc5d342ef65b00f68d239c62919f60f3986d74abf7a37b955b296cb805e",
    ),
    "isosceles-trapezoid-bases-cosine-leg": (
        "42c396d3-3418-40f8-b80e-1eb6102702a1",
        (),
        "8bd9b2b16cb1319f6b4223c912013c7d7cc31a9a147376942c9b05e8ff055d3a",
    ),
    "isosceles-trapezoid-leg-sine-small-base": (
        "42c396d3-3418-40f8-b80e-1eb6102702a1",
        (),
        "08d05febc7e4099152451c5a14beb6f7ed592688c82fdd1fa37e017f30a82513",
    ),
    "isosceles-trapezoid-bases-tangent-height": (
        "42c396d3-3418-40f8-b80e-1eb6102702a1",
        (),
        "c54b9b8de2e06b4d74f2cc2589bd22b851979fca4a9b080930909893adc49e62",
    ),
    "isosceles-trapezoid-height-tangent-large-base": (
        "42c396d3-3418-40f8-b80e-1eb6102702a1",
        (),
        "427d8468c5dde8965b7db8f7f91569967c78e8e89b2283365d2f30c3c1a886f1",
    ),
    "isosceles-trapezoid-bases-height-tangent": (
        "42c396d3-3418-40f8-b80e-1eb6102702a1",
        (),
        "d66a1d7d7165ad3db2240b2ec85dbca26b2dc2b7a27e58d6e1f925804e4cdd3c",
    ),
    "isosceles-trapezoid-bases-perimeter-area": (
        "c37ee594-116d-4c12-ab84-5fb6f074d03c",
        (("image_2", "157aa0f8-ea5d-419c-b075-9864f88d2a85"),),
        "313e6a04a2bc8989c5caf4a2b2cb286f7dd206d3d2dc0e26cf6fcb48bd8d6997",
    ),
    "isosceles-trapezoid-bases-area-perimeter": (
        "c37ee594-116d-4c12-ab84-5fb6f074d03c",
        (("image_2", "157aa0f8-ea5d-419c-b075-9864f88d2a85"),),
        "b4878b01c9facfeab40d9761dc40915ee7e2452ea4324c7452f72c4fb88f73a2",
    ),
    "isosceles-trapezoid-bases-leg-area": (
        "3be35d9e-e571-40e8-8a82-e1a0366359ac",
        (("image_2", "a7aa0827-7b1f-4364-8469-437dfe2fe497"),),
        "80f2d34d1645ca44edaffd3328b0588bb46f57dbf3333100d64c6105a24a417a",
    ),
    "isosceles-trapezoid-bases-area-leg": (
        "3be35d9e-e571-40e8-8a82-e1a0366359ac",
        (("image_2", "a7aa0827-7b1f-4364-8469-437dfe2fe497"),),
        "3fdfc407f7684b79c5a4b357fcffc36eb41bd6d44ae71a983844e786ad60941d",
    ),
    "isosceles-trapezoid-leg-sixty-small-base": (
        "3be35d9e-e571-40e8-8a82-e1a0366359ac",
        (("image_2", "a7aa0827-7b1f-4364-8469-437dfe2fe497"),),
        "c502451db471ed092df36a66b1d39008aa36269952eea15ae25bc2ffd27d904c",
    ),
    "isosceles-trapezoid-bases-sixty-perimeter": (
        "3be35d9e-e571-40e8-8a82-e1a0366359ac",
        (("image_2", "a7aa0827-7b1f-4364-8469-437dfe2fe497"),),
        "b4927efc27210f94872734690d0dbff19785a12ce24c8e11276d4933084387e7",
    ),
    "isosceles-trapezoid-bases-fortyfive-height": (
        "590b89bd-3f93-494c-a26c-e162137e6f71",
        (("image_2", "d64f66e0-9b41-447f-8d93-e95acc9eb921"),),
        "d86e44017a05220518cbb0b7cfe48e0396ca1013f25eecacf0e0b676bb11bdda",
    ),
}
SOURCES = {
    "590b89bd-3f93-494c-a26c-e162137e6f71": (
        "590b89bd-3f93-494c-a26c-e162137e6f71",
        "8cccc1d73b7ca536e900666065d06e22bd462ec3525b3acb07162bf0ee326488",
    ),
    "d64f66e0-9b41-447f-8d93-e95acc9eb921": (
        "d64f66e0-9b41-447f-8d93-e95acc9eb921",
        "c5673ca823df417d73c93e01e2d7055f4ff2811e9964e8c7d62d0fd2e59ed82e",
    ),
    "c37ee594-116d-4c12-ab84-5fb6f074d03c": (
        "3be35d9e-e571-40e8-8a82-e1a0366359ac",
        "ec67cfe0dd333db04ae11e705af64e8d57a7a7ae09241fe56eeb98a3ed61ef38",
    ),
    "3be35d9e-e571-40e8-8a82-e1a0366359ac": (
        "3be35d9e-e571-40e8-8a82-e1a0366359ac",
        "ec67cfe0dd333db04ae11e705af64e8d57a7a7ae09241fe56eeb98a3ed61ef38",
    ),
    "46d25626-a77d-4eaf-bcef-1bb477ec17e0": (
        "46d25626-a77d-4eaf-bcef-1bb477ec17e0",
        "6f28d812db859af728b97302c8caeb6d63af38c0a4e7da656ef9f7234fd86324",
    ),
    "42c396d3-3418-40f8-b80e-1eb6102702a1": (
        "42c396d3-3418-40f8-b80e-1eb6102702a1",
        "d6bfb4ca7f394df357a466b6e314efb67b4abc996009ca93d31e192af5987ee9",
    ),
    "157aa0f8-ea5d-419c-b075-9864f88d2a85": (
        "a7aa0827-7b1f-4364-8469-437dfe2fe497",
        "324847f731e027e12a8da51af4a68988c0409b8fac14f09573c8f3f1ad8c2e12",
    ),
    "a7aa0827-7b1f-4364-8469-437dfe2fe497": (
        "a7aa0827-7b1f-4364-8469-437dfe2fe497",
        "324847f731e027e12a8da51af4a68988c0409b8fac14f09573c8f3f1ad8c2e12",
    ),
}


def source_bytes(source):
    if source not in SOURCES:
        raise ContentPlanError("the isosceles-trapezoid source needs a review")
    canonical, digest = SOURCES[source]
    raw = gzip.decompress(
        files(__package__).joinpath("assets/" + canonical + ".svgz").read_bytes()
    )
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ContentPlanError("the reviewed isosceles-trapezoid SVG changed")
    return raw


def review_parent(rule, primary, html, assets):
    if rule not in PARENTS:
        raise ContentPlanError("an explicit reviewed trapezoid rule is required")
    expected, figures, digest = PARENTS[rule]
    if (
        primary != expected
        or not isinstance(html, str)
        or hashlib.sha256(html.encode()).hexdigest() != digest
    ):
        raise ContentPlanError("the complete reviewed trapezoid parent changed")
    if not isinstance(assets, (tuple, list)) or any(
        not isinstance(a, dict) for a in assets
    ):
        raise ContentPlanError("complete trapezoid parent asset metadata is required")
    if [(a.get("asset_key"), a.get("source_asset_id")) for a in assets] != list(
        figures
    ) or any(a.get("url") != "/assets/" + a["source_asset_id"] for a in assets):
        raise ContentPlanError("the reviewed trapezoid solution figures changed")
    for source in (primary, *(s for _, s in figures)):
        source_bytes(source)
