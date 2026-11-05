"""Pin exact numeric drawings and refuse incomplete named-vertex measurements."""

import hashlib
import json
from importlib.resources import files

from ..core.errors import ContentPlanError
from . import source_assets
from .orthogonal_element_geometry import frame

DATA = json.loads(
    files(__package__).joinpath("assets/orthogonal_element_sources.json").read_text()
)
PARENTS = {
    rule: (primary, tuple(tuple(a) for a in pictures), digest)
    for rule, (primary, pictures, digest) in DATA["parents"].items()
}
METHODS = DATA["methods"]


def review_parent(rule, primary, html, assets):
    source_assets.review_parent(
        rule, primary, html, assets, parents=PARENTS, sources=DATA["sources"]
    )
    points(primary)


def source_bytes(source):
    return source_assets.source_bytes(source, DATA["sources"])


def points(source):
    raw = source_bytes(source)
    if source in DATA["pending"]:
        raise ContentPlanError(DATA["pending"][source])
    review = DATA["figures"].get(source)
    if not review or review["sha256"] != hashlib.sha256(raw).hexdigest():
        raise ContentPlanError("the named vertices belong to another diagram revision")
    return frame(review["kind"], review["given"])
