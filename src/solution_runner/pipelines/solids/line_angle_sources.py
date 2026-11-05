"""Pin the complete line-angle parent and its unlabelled spatial diagram."""

from . import source_assets

RULE = "solid-box-line-sine"
SOURCE = "0b5fae13-db30-4836-b432-228dddd1eb62"
PARENTS = {
    RULE: (
        SOURCE,
        (("image_1", SOURCE),),
        "9abeb55d6c2c0e8f1eb4a2fefbcda4963eb8b07c3ce5740fe4c230b652a290f6",
    )
}
SOURCES = {
    SOURCE: (SOURCE, "0e328dcb47b8a9f9c10c93fdc50f60348114235f671fac63ffbba6ef28802817")
}


def source_bytes():
    return source_assets.source_bytes(SOURCE, SOURCES)


def review_parent(rule, primary, html, assets):
    return source_assets.review_parent(
        rule, primary, html, assets, parents=PARENTS, sources=SOURCES
    )
