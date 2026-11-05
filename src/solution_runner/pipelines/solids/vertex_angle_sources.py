"""Reviewed angle parent methods, figure roles, numeric labels and helper segments."""

from . import source_assets

PARENTS = {
    "solid-box-angle-from-face-diagonal": (
        "50bc8b3b-c24f-48f2-bb1c-1a41f4f46e63",
        (("image_2", "8b1e6c2a-fdbe-4d22-bd94-89ef488e18f2"),),
        "4310627f72d8b800815f418f51a03fffabc1f991aefc7b8d0733eeb1b51e3970",
    ),
    "solid-box-angle-from-base-diagonal": (
        "c6f82a07-d4e0-4232-a4ad-5fcb3ba5590b",
        (),
        "6c013fe0c9d157a3938b301d178827da290234023ec48e32062a307828f3fe87",
    ),
}
SOURCES = {
    "50bc8b3b-c24f-48f2-bb1c-1a41f4f46e63": (
        "50bc8b3b-c24f-48f2-bb1c-1a41f4f46e63",
        "c0a0887c48e06f6731afe7901092a8a09440d4be73d6bebee59647c922b781dc",
    ),
    "8b1e6c2a-fdbe-4d22-bd94-89ef488e18f2": (
        "8b1e6c2a-fdbe-4d22-bd94-89ef488e18f2",
        "9c2c8c2d7cb55a1bcffc0fcb9618621b8e092fc946e40d52499aac80508a0c60",
    ),
    "ef22aa49-450e-445c-b231-981065f69a67": (
        "ef22aa49-450e-445c-b231-981065f69a67",
        "3af6432794c81ff962e1e8d48946208ec641aefe82d8fbf55b830a28b7f06d6e",
    ),
    "830a265c-aa42-4ac6-90b2-40621ff60a8e": (
        "830a265c-aa42-4ac6-90b2-40621ff60a8e",
        "29451de25ac10c514d822ea7df31113e9b9ff32986edba5f8a2632d3897419ed",
    ),
    "d04cd2a8-7ba8-4c6a-aa99-a2169227571a": (
        "d04cd2a8-7ba8-4c6a-aa99-a2169227571a",
        "6137b874afb6018863356da6ebebf5c1c3d4a832e613ac8835185ea8b493e24c",
    ),
    "99e19cfb-6c2e-4878-bca3-73187eb1cfc0": (
        "99e19cfb-6c2e-4878-bca3-73187eb1cfc0",
        "d580655c1fe2abc953143f6584c1c1c67d29fd81f4d729a27467d92bc28eeba1",
    ),
    "c6f82a07-d4e0-4232-a4ad-5fcb3ba5590b": (
        "c6f82a07-d4e0-4232-a4ad-5fcb3ba5590b",
        "b3ef4e20b410838692c8477fbbd0ac7efe4f628711429a6be4574f643e549435",
    ),
    "79867b1e-a6e6-4f80-a6e4-6c96d8b990c2": (
        "79867b1e-a6e6-4f80-a6e4-6c96d8b990c2",
        "c37b145cf2b2c3e34c7bcbda9c4b07189102b0cf42637fcd2b4cb5e90015f06f",
    ),
    "da473b9b-129b-4a1c-9208-2ff6f71c1ecd": (
        "da473b9b-129b-4a1c-9208-2ff6f71c1ecd",
        "faa0d84404df895de0abf38dab59785006e0a9d2565b4328747d5bf3af1cfd76",
    ),
    "9b447320-c919-4e84-8a4d-bb2e06dda9c0": (
        "9b447320-c919-4e84-8a4d-bb2e06dda9c0",
        "698efff62545790d57cd3f294c570a48cb0ea13455109ba078e69c465cfb2d11",
    ),
}
FIGURES = {
    "50bc8b3b-c24f-48f2-bb1c-1a41f4f46e63": {
        "dimensions": None,
        "helpers": (),
        "angle": None,
        "role": "condition",
    },
    "8b1e6c2a-fdbe-4d22-bd94-89ef488e18f2": {
        "dimensions": ("25", "16", "9"),
        "helpers": (("A", "D_1"), ("B", "D_1")),
        "angle": None,
        "role": "solution",
    },
    "ef22aa49-450e-445c-b231-981065f69a67": {
        "dimensions": None,
        "helpers": (),
        "angle": None,
        "role": "condition",
    },
    "830a265c-aa42-4ac6-90b2-40621ff60a8e": {
        "dimensions": ("289", "64", "225"),
        "helpers": (("A", "D_1"), ("B", "D_1")),
        "angle": None,
        "role": "solution",
    },
    "d04cd2a8-7ba8-4c6a-aa99-a2169227571a": {
        "dimensions": None,
        "helpers": (),
        "angle": None,
        "role": "condition",
    },
    "99e19cfb-6c2e-4878-bca3-73187eb1cfc0": {
        "dimensions": ("144", "81", "225"),
        "helpers": (("B_1", "D"), ("B_1", "D_1")),
        "angle": None,
        "role": "solution",
    },
    "c6f82a07-d4e0-4232-a4ad-5fcb3ba5590b": {
        "dimensions": ("16", "9", "25"),
        "helpers": (("B", "D"), ("B", "D_1")),
        "angle": "DBD_1",
        "role": "condition",
    },
    "79867b1e-a6e6-4f80-a6e4-6c96d8b990c2": {
        "dimensions": ("25", "16", "16"),
        "helpers": (("B", "C_1"),),
        "angle": "C_1BC",
        "role": "condition",
    },
    "da473b9b-129b-4a1c-9208-2ff6f71c1ecd": {
        "dimensions": None,
        "helpers": (("B", "D_1"), ("B_1", "D_1")),
        "angle": None,
        "role": "condition",
    },
    "9b447320-c919-4e84-8a4d-bb2e06dda9c0": {
        "dimensions": ("144", "81", "225"),
        "helpers": (("A", "C"), ("A_1", "C")),
        "angle": None,
        "role": "condition",
    },
}
MEMBERS = {
    "solid-box-angle-from-face-diagonal": (
        "50bc8b3b-c24f-48f2-bb1c-1a41f4f46e63",
        "8b1e6c2a-fdbe-4d22-bd94-89ef488e18f2",
        "ef22aa49-450e-445c-b231-981065f69a67",
        "830a265c-aa42-4ac6-90b2-40621ff60a8e",
        "d04cd2a8-7ba8-4c6a-aa99-a2169227571a",
        "99e19cfb-6c2e-4878-bca3-73187eb1cfc0",
    ),
    "solid-box-angle-from-base-diagonal": (
        "c6f82a07-d4e0-4232-a4ad-5fcb3ba5590b",
        "79867b1e-a6e6-4f80-a6e4-6c96d8b990c2",
        "da473b9b-129b-4a1c-9208-2ff6f71c1ecd",
        "9b447320-c919-4e84-8a4d-bb2e06dda9c0",
    ),
}


def source_bytes(source):
    return source_assets.source_bytes(source, SOURCES)


def review_parent(rule, primary, html, assets):
    return source_assets.review_parent(
        rule, primary, html, assets, parents=PARENTS, sources=SOURCES
    )
