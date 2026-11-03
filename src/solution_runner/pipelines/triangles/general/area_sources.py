"""Pinned source lettering and parent methods for elementary triangle areas."""

import gzip
import hashlib
from importlib.resources import files

from ...core.errors import ContentPlanError

SAS = "4e20eaee-c328-4838-a749-0e6c1343eb60"
HEIGHTS = "b558b62a-346c-4553-987d-f417cd5132b7"
_HASHES = {
    SAS: "439f0ae368bcb6d846bbcb12d57589bd194a68be35f77fc6dd0e69587b50c749",
    HEIGHTS: "f75dbe780259ea12cc003ae3d394f474f3bfea78f2e18711de15d0ef6bd7c01b",
}
PARENTS = {
    "27591": "85bcd02971a23533300de59a320cc05d63c0d0b86348675c922cdb1ef897d7d6",
    "27623": "cbdcf7849887b325c41c29b55a32594e754573e5de8f6cdd3ce1090f81945301",
}


def source_bytes(source):
    if source not in _HASHES:
        raise ContentPlanError("the triangle area source needs review")
    raw = gzip.decompress(
        files(__package__).joinpath("assets/" + source + ".svgz").read_bytes()
    )
    if hashlib.sha256(raw).hexdigest() != _HASHES[source]:
        raise ContentPlanError("the audited triangle area source changed")
    return raw


def review_parent(html, group):
    if (
        not isinstance(html, str)
        or hashlib.sha256(html.encode()).hexdigest() != PARENTS[group]
    ):
        raise ContentPlanError(
            "the complete triangle area parent method must be reviewed"
        )
