"""Pin reviewed cylinder methods and mathematically identified unnumbered figures."""

from . import source_assets
from .cylinder_cut import DATA as CUT_DATA

PARENTS = {
    "solid-cylinder-immersed-displacement": (
        "6a9b9977-189d-4517-beba-1c2a0a82e51c",
        (),
        "a62febb7d637825a1387ab3cd47998396e8a52ad56f5e2de23aa1f425c4169fb",
    ),
    "solid-cylinder-liquid-transfer": (
        "a8b286be-6a64-4748-be89-9768c4cb8de9",
        (),
        "3d0e97c4481d5018005a6fa7896dfdc3c62c154d56a03a546baa6843cdfe5442",
    ),
    "solid-cylinder-volume-scaling": (
        None,
        (),
        "dceceb1cc35db5d42e80e178a906a5b75c772f505f665f594c5bd3fb93bf0f6a",
    ),
    "solid-cylinder-lateral-from-radius": (
        "5209585b-38b8-45a9-ace4-35712364c282",
        (),
        "af73296f44e4698bebb745a5c62e541b3299dc743836e882109d4f6b4a31144e",
    ),
    "solid-cylinder-lateral-from-circumference": (
        "5209585b-38b8-45a9-ace4-35712364c282",
        (),
        "d600cd6cdb09dc13d531f20a2d5d10d00cfa462fc8b59c8057ab8bdb72403a68",
    ),
    "solid-cylinder-lateral-from-axial-area": (
        "3b0fb301-3f6f-4c93-ae42-89c547017e1e",
        (),
        "954a8998db547fbb8fd9a44f589a9d23e7af159fc72d3033c0807967c38e8d9d",
    ),
    "solid-cylinder-height-from-circumference": (
        "d9a6d82b-867c-4e92-9008-ad8effb419c2",
        (),
        "ac2990b1d1c5398168ede4faf4527f68103c4592697e06ffab7c8022abac5395",
    ),
    "solid-cylinder-height-from-diameter": (
        "7a10fe04-190a-4ac4-b0a8-4f6c58edbcb2",
        (),
        "2735f02a8bca6d2d0907d953241e1f46bf9a21c62957f42f1ab1845c3db65152",
    ),
    "solid-cylinder-diameter-from-lateral": (
        "f421f999-42e5-497b-8387-9b0a26dcf645",
        (("image_1", "f421f999-42e5-497b-8387-9b0a26dcf645"),),
        "3117064c199122b7a400dd316a145aeecc9cfa48ebbfcaf741b5db4544beded9",
    ),
}
RULES = {
    "solid-cylinder-immersed-displacement": "displacement",
    "solid-cylinder-liquid-transfer": "transfer",
    "solid-cylinder-volume-scaling": "volume_ratio",
    "solid-cylinder-lateral-from-radius": "lateral",
    "solid-cylinder-lateral-from-circumference": "lateral",
    "solid-cylinder-lateral-from-axial-area": "axial_lateral",
    "solid-cylinder-height-from-circumference": "height",
    "solid-cylinder-height-from-diameter": "height",
    "solid-cylinder-diameter-from-lateral": "diameter",
}
SOURCES = {
    "6a9b9977-189d-4517-beba-1c2a0a82e51c": (
        "6a9b9977-189d-4517-beba-1c2a0a82e51c",
        "be0e07b1a47108c0d2f09165e217199133ae2e32c957e9efe4f25a7231077e60",
    ),
    "a8b286be-6a64-4748-be89-9768c4cb8de9": (
        "a8b286be-6a64-4748-be89-9768c4cb8de9",
        "4343c43177c02862e83671400583ae88e540307878c52717dc4223d1a0d0f7c8",
    ),
    "888f9f28-5f69-4052-b73c-5f7da2b2abc6": (
        "888f9f28-5f69-4052-b73c-5f7da2b2abc6",
        "aae917231a8b62172131b8104f5a06827d6575ecd4205fc906a1160bfbd6b0b6",
    ),
    "5209585b-38b8-45a9-ace4-35712364c282": (
        "5209585b-38b8-45a9-ace4-35712364c282",
        "74ad7164e80bad8037107f9f1d78dad12f1565c82e2344f0b11ab8e6e3cdc6a7",
    ),
    "3b0fb301-3f6f-4c93-ae42-89c547017e1e": (
        "3b0fb301-3f6f-4c93-ae42-89c547017e1e",
        "19a02774d11e145403c66f99deeb780cd2845f68e3c67f63557bad27a103608b",
    ),
    "d9a6d82b-867c-4e92-9008-ad8effb419c2": (
        "d9a6d82b-867c-4e92-9008-ad8effb419c2",
        "c053627b0231f04049b1fa8afede07081507831367f3d5599aaef40aefc0c5f9",
    ),
    "7a10fe04-190a-4ac4-b0a8-4f6c58edbcb2": (
        "7a10fe04-190a-4ac4-b0a8-4f6c58edbcb2",
        "54f31b27560a7d3912c28edc4de3e190d6f6c375804df3fc91e498d2d1eeb9c0",
    ),
    "e8d2f001-6fc2-4340-a672-9bd835b8f051": (
        "e8d2f001-6fc2-4340-a672-9bd835b8f051",
        "eaec9caca702142490f849049ef5091e8f05b7a4bbf83d0ae506dcfa2aa58583",
    ),
    "f421f999-42e5-497b-8387-9b0a26dcf645": (
        "7a10fe04-190a-4ac4-b0a8-4f6c58edbcb2",
        "54f31b27560a7d3912c28edc4de3e190d6f6c375804df3fc91e498d2d1eeb9c0",
    ),
}
BASIC = (
    "5209585b-38b8-45a9-ace4-35712364c282",
    "d9a6d82b-867c-4e92-9008-ad8effb419c2",
    "7a10fe04-190a-4ac4-b0a8-4f6c58edbcb2",
    "e8d2f001-6fc2-4340-a672-9bd835b8f051",
    "f421f999-42e5-497b-8387-9b0a26dcf645",
)
MODE_SOURCES = {
    "displacement": ("6a9b9977-189d-4517-beba-1c2a0a82e51c",),
    "transfer": (
        "a8b286be-6a64-4748-be89-9768c4cb8de9",
        "888f9f28-5f69-4052-b73c-5f7da2b2abc6",
    ),
    "volume_ratio": (),
    "lateral": BASIC,
    "height": BASIC,
    "diameter": BASIC,
    "axial_lateral": ("3b0fb301-3f6f-4c93-ae42-89c547017e1e",),
}


PARENTS.update(CUT_DATA["parents"])
RULES.update(CUT_DATA["rules"])
SOURCES.update(CUT_DATA["sources"])
for _mode in ("sector", "stepped", "annular"):
    MODE_SOURCES[_mode] = tuple(
        source for source, f in CUT_DATA["figures"].items() if f["mode"] == _mode
    )


def source_bytes(source):
    return source_assets.source_bytes(source, SOURCES)


def review_parent(rule, primary, html, assets):
    return source_assets.review_parent(
        rule, primary, html, assets, parents=PARENTS, sources=SOURCES
    )
