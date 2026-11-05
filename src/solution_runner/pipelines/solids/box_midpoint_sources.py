"""Pin midpoint section parents and exact source geometry, including bare K diagrams."""

from . import source_assets

PARENTS = {
    "solid-box-midpoint-section": (
        "2efaf127-5406-4957-bb86-06b45529b757",
        (("image_1", "2efaf127-5406-4957-bb86-06b45529b757"),),
        "739aedcb1ae7dfd1c8ffd66b620d058f085b18904e9d4a1da0da964007c209ec",
    )
}
SOURCES = {
    "2efaf127-5406-4957-bb86-06b45529b757": (
        "2efaf127-5406-4957-bb86-06b45529b757",
        "c6309be15372bc910ca4fbbb03e7ef668671aa1603e1be0e2dbbcf6675cfb0c6",
    ),
    "58692e88-f3ef-4bb5-964c-2214c02500d3": (
        "58692e88-f3ef-4bb5-964c-2214c02500d3",
        "24d5b9d1a2e299baca9ca1a8be52082ca33000f9a9445613fcad741e9743fd80",
    ),
    "e02d6e2f-e656-485c-abbc-439c1790cd86": (
        "e02d6e2f-e656-485c-abbc-439c1790cd86",
        "7d07178efdd234fd26ed611dd489c258c5f9544bf11637e6cbe73a20cc56dc8e",
    ),
    "13133a9e-b338-4edb-9eab-d207ac80ddaf": (
        "13133a9e-b338-4edb-9eab-d207ac80ddaf",
        "a505bba9801d00fa4227d8ef29e288861151dc669b01e1e003ec412d08a67497",
    ),
    "6ce0d751-db14-4b9e-9733-02a6d1000f75": (
        "6ce0d751-db14-4b9e-9733-02a6d1000f75",
        "20d9ba1d5f455510047f4fdb3b0e6b9e3b21beccad359e4571733b5aff9b2156",
    ),
}
FIGURES = {
    "2efaf127-5406-4957-bb86-06b45529b757": ("solution", "B", ("A_1", "D_1")),
    "58692e88-f3ef-4bb5-964c-2214c02500d3": ("condition", "C", ("A_1", "B_1")),
    "e02d6e2f-e656-485c-abbc-439c1790cd86": ("solution", "C", ("A_1", "B_1")),
    "13133a9e-b338-4edb-9eab-d207ac80ddaf": ("condition", "D", ("B_1", "C_1")),
    "6ce0d751-db14-4b9e-9733-02a6d1000f75": ("solution", "D", ("B_1", "C_1")),
}


def source_bytes(source):
    return source_assets.source_bytes(source, SOURCES)


def review_parent(rule, primary, html, assets):
    return source_assets.review_parent(
        rule, primary, html, assets, parents=PARENTS, sources=SOURCES
    )
