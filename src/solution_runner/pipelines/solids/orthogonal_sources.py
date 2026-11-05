"""Pin complete orthogonal parent methods and versioned numeric SVG/PNG transcriptions."""

import hashlib
import json
from importlib.resources import files

from ..core.errors import ContentPlanError
from . import source_assets

DATA = json.loads(
    files(__package__).joinpath("assets/orthogonal_sources.json").read_text()
)
SOURCES = DATA["sources"]
PARENTS = {
    rule: (primary, tuple(tuple(a) for a in pictures), digest)
    for rule, (primary, pictures, digest) in DATA["parents"].items()
}
RULES = DATA["rules"]


def source_bytes(source):
    raw = source_assets.source_bytes(source, SOURCES)
    review = DATA["figures"].get(source)
    if not review or review["sha256"] != hashlib.sha256(raw).hexdigest():
        raise ContentPlanError(
            "the numeric solid transcription belongs to another diagram revision"
        )
    return raw


def review_parent(rule, primary, html, assets):
    source_assets.review_parent(
        rule, primary, html, assets, parents=PARENTS, sources=SOURCES
    )
    if primary is not None:
        source_bytes(primary)
