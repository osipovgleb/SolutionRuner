"""Pin complete prism parent methods, compatible diagrams and actual section vertices."""

import json
from importlib.resources import files

from ..core.errors import ContentPlanError
from . import source_assets

DATA = json.loads(files(__package__).joinpath("assets/prism_sources.json").read_text())
PARENTS = {
    rule: (primary, tuple(tuple(a) for a in figures), digest)
    for rule, (primary, figures, digest) in DATA["parents"].items()
}
RULES = DATA["rules"]
SOURCES = DATA["sources"]
DEFAULTS = DATA["defaults"]


def compatible(m, key, source, role):
    f = DATA["figures"].get(source)
    if not f or m.kind not in f["kinds"] or [key, role] not in f["slots"]:
        raise ContentPlanError(
            "the prism figure depicts another object, cut or section role"
        )
    if "vertex_sets" in f and (
        m.solid is None or sorted(m.solid.vertices) not in f["vertex_sets"]
    ):
        raise ContentPlanError(
            "the highlighted prism vertices differ from the actual question"
        )
    source_bytes(source)


def source_bytes(source):
    return source_assets.source_bytes(source, SOURCES)


def review_parent(rule, primary, html, assets):
    return source_assets.review_parent(
        rule, primary, html, assets, parents=PARENTS, sources=SOURCES
    )
