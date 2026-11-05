"""Read exact reviewed solid diagrams and verify complete parent method pins."""

import gzip
import hashlib
from importlib.resources import files

from ..core.errors import ContentPlanError


def source_bytes(source, sources):
    if source not in sources:
        raise ContentPlanError("the solid diagram needs review")
    canonical, digest = sources[source]
    name = canonical if canonical.endswith(".png") else canonical + ".svgz"
    raw = files(__package__).joinpath("assets/" + name).read_bytes()
    if name.endswith(".svgz"):
        raw = gzip.decompress(raw)
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ContentPlanError("the reviewed solid diagram changed")
    return raw


def review_parent(rule, primary, html, assets, *, parents, sources):
    if rule not in parents:
        raise ContentPlanError("an explicit reviewed solid rule is required")
    expected, figures, digest = parents[rule]
    if expected is None and primary == "":
        primary = None
    if (
        primary != expected
        or not isinstance(html, str)
        or hashlib.sha256(html.encode()).hexdigest() != digest
    ):
        raise ContentPlanError("the complete reviewed solid parent changed")
    if not isinstance(assets, (tuple, list)) or any(
        not isinstance(a, dict) for a in assets
    ):
        raise ContentPlanError("complete solid parent asset metadata is required")
    if [(a.get("asset_key"), a.get("source_asset_id")) for a in assets] != list(
        figures
    ) or any(a.get("url") != "/assets/" + a["source_asset_id"] for a in assets):
        raise ContentPlanError("the reviewed solid solution figures changed")
    for source in (primary, *(s for _, s in figures)):
        if source is not None:
            source_bytes(source, sources)
