"""Pin complete cone parent methods and compatible original drawing roles."""

import json
from importlib.resources import files

from ..core.errors import ContentPlanError
from . import source_assets

DATA = json.loads(files(__package__).joinpath("assets/cone_sources.json").read_text())
PARENTS = {
    rule: (p, tuple(tuple(v) for v in figures), digest)
    for rule, (p, figures, digest) in DATA["parents"].items()
}
RULES = DATA["rules"]
SOURCES = DATA["sources"]
BASIC = (
    "c66e1981-92e4-42b7-9357-575a61145152",
    "fc82d4c2-f41f-43e6-a582-5fbdaab09bb0",
    "fd20d1f7-0fa8-4a47-91c3-0a7c029be2b6",
)
AXIAL = (
    "263bac88-7917-46e3-96aa-cbf8d88af825",
    "210f48b4-3615-4987-863b-79269c82ccf6",
    "a7d4a515-c8ce-40d4-a1f1-8b3f357e9d39",
)
SIMILAR = (
    "f5ca1d9c-7d64-41cb-843a-990448ffc339",
    "f0f25382-813c-4733-9bf7-1b7eeda05468",
    "cf466337-d933-4b7f-ad5d-93f3a506ddb4",
    "b9d80bf1-7f90-401b-ac46-e05dd7b0972f",
)
LIQUID = (
    "ece8498a-68b2-459a-9973-53c706b2d20e",
    "c720ca97-fc9c-4807-aca2-05b8617e4fdb",
    "68edfc62-dce7-4b3c-97db-0b2669d062b7",
)
NUMBERED = "30afa840-b907-426f-9ae9-910c180b5526"


def compatible(m, source):
    if m.mode == "similarity":
        allowed = LIQUID if m.kind == "liquid" else SIMILAR
    elif m.input_kind == "diameter_apex":
        allowed = ("0005dd49-93f6-4a3e-96d6-a5424acc7f08",)
    elif m.input_kind == "rotation":
        allowed = ("d97c3614-2d40-4659-aaac-24ddd93dd314",)
    elif m.input_kind == "slant_angle":
        allowed = BASIC + (NUMBERED,)
    else:
        allowed = AXIAL if m.kind == "axial" else BASIC
    if source not in allowed or source == NUMBERED and m.given != (44, 30):
        raise ContentPlanError(
            "the cone diagram or its numbered dimensions differ from the actual question"
        )
    source_bytes(source)


def source_bytes(source):
    return source_assets.source_bytes(source, SOURCES)


def review_parent(rule, primary, html, assets):
    return source_assets.review_parent(
        rule, primary, html, assets, parents=PARENTS, sources=SOURCES
    )
