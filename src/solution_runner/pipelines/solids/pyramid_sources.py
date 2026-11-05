"""Pin reviewed pyramid methods, source bytes and numerical diagram transcriptions."""

import hashlib
import json
from importlib.resources import files

from ..core.errors import ContentPlanError
from . import source_assets

DATA = json.loads(
    files(__package__).joinpath("assets/pyramid_sources.json").read_text()
)
SOURCES = DATA["sources"]
PARENTS = {
    rule: (primary, tuple(tuple(a) for a in figures), digest)
    for rule, (primary, figures, digest) in DATA["parents"].items()
}
RULES = DATA["rules"]


def source_bytes(source):
    raw = source_assets.source_bytes(source, SOURCES)
    transcription = DATA["floor"].get(source)
    if transcription and hashlib.sha256(raw).hexdigest() != transcription["sha256"]:
        raise ContentPlanError(
            "the numerical pyramid transcription belongs to another source revision"
        )
    return raw


def review_parent(rule, primary, html, assets):
    return source_assets.review_parent(
        rule, primary, html, assets, parents=PARENTS, sources=SOURCES
    )
