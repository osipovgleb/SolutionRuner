"""Pin complete parent methods and exact compatible solid-combination sources."""

import json
from importlib.resources import files

from . import source_assets

DATA = json.loads(
    files(__package__).joinpath("assets/combined_sources.json").read_text()
)
SOURCES = DATA["sources"]
PARENTS = {
    rule: (primary, tuple(tuple(a) for a in figures), digest)
    for rule, (primary, figures, digest) in DATA["parents"].items()
}
RULES = DATA["rules"]


def source_bytes(source):
    return source_assets.source_bytes(source, SOURCES)


def review_parent(rule, primary, html, assets):
    return source_assets.review_parent(
        rule, primary, html, assets, parents=PARENTS, sources=SOURCES
    )
