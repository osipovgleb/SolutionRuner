"""Pin reviewed section parents and unnumbered, geometrically identified diagrams."""

from . import source_assets

PARENTS = {
    "solid-box-vertical-section": (
        "0b5fae13-db30-4836-b432-228dddd1eb62",
        (("image_1", "0b5fae13-db30-4836-b432-228dddd1eb62"),),
        "9af18025a8384cf7108454ec956733c97a2eaca9373507ff4f57e241e3a18c27",
    ),
    "solid-box-oblique-section": (
        "fa12724f-ab48-4029-b612-8821c8f857d1",
        (("image_1", "fa12724f-ab48-4029-b612-8821c8f857d1"),),
        "c7ca2e7b7df09f84dafc4eefb22f9723f8507bb98a43b4e7e5c8b36de734687d",
    ),
}
SOURCES = {
    "0b5fae13-db30-4836-b432-228dddd1eb62": (
        "0b5fae13-db30-4836-b432-228dddd1eb62",
        "0e328dcb47b8a9f9c10c93fdc50f60348114235f671fac63ffbba6ef28802817",
    ),
    "7cdf3068-3884-4f42-9c6a-9edf71f5cc6e": (
        "7cdf3068-3884-4f42-9c6a-9edf71f5cc6e",
        "45d987ecdded5b0eaaa8aeb917ed4fb597bd25ebc3da249149a1473e654e941e",
    ),
    "dfa5e2e3-a7b8-431e-b6b7-f6f6e6f42ba7": (
        "dfa5e2e3-a7b8-431e-b6b7-f6f6e6f42ba7",
        "a8d75181109acc3a10706063181b6455e79037de1eeb6174baf2701713cbb870",
    ),
    "fa12724f-ab48-4029-b612-8821c8f857d1": (
        "fa12724f-ab48-4029-b612-8821c8f857d1",
        "0dd39fc46e7513a81f0487ea2819b170aad1ab210c052cac2b176e7c98fd3902",
    ),
    "e7f8d3df-0173-4e6f-a898-9b06616a3d4e": (
        "fa12724f-ab48-4029-b612-8821c8f857d1",
        "0dd39fc46e7513a81f0487ea2819b170aad1ab210c052cac2b176e7c98fd3902",
    ),
}
FIGURES = {
    "0b5fae13-db30-4836-b432-228dddd1eb62": ("A", "A_1", "C", "C_1"),
    "7cdf3068-3884-4f42-9c6a-9edf71f5cc6e": ("A", "B", "C_1", "D_1"),
    "dfa5e2e3-a7b8-431e-b6b7-f6f6e6f42ba7": ("A", "B", "C_1", "D_1"),
    "fa12724f-ab48-4029-b612-8821c8f857d1": ("A", "B", "C_1", "D_1"),
    "e7f8d3df-0173-4e6f-a898-9b06616a3d4e": ("A", "B", "C_1", "D_1"),
}


def source_bytes(source):
    return source_assets.source_bytes(source, SOURCES)


def review_parent(rule, primary, html, assets):
    return source_assets.review_parent(
        rule, primary, html, assets, parents=PARENTS, sources=SOURCES
    )
