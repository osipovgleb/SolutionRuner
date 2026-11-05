"""Reviewed spatial-distance parents, numeric figures and marked segments."""

RULES = {
    "solid-box-distance-squared": "distance_squared",
    "solid-box-vertex-distance": "distance",
    "solid-box-missing-edge": "edge",
    "solid-box-space-diagonal": "diagonal",
}

PARENTS = {
    "solid-box-distance-squared": (
        "f4689cbc-e217-4787-85bf-30a406dc5ce7",
        (("image_2", "626ee550-5e35-469c-b555-65cb5466e6ea"),),
        "d570ff7c9e491b2063f8b0ccbc60f5301335383ea5d68110bef1a0004ec3e8ac",
    ),
    "solid-box-vertex-distance": (
        "6c17c081-08ea-43fa-9da5-5fb7a08387a2",
        (("image_2", "66d11cfd-6c56-4268-8b85-6e4549417bbe"),),
        "520447e0d6fd2f3a023da9984dec696fb86988841c9493ee0861223840466e1c",
    ),
    "solid-box-missing-edge": (
        "e8daeb88-d29f-4113-8de3-1bbe5e85bb48",
        (),
        "64ee5703808412af4121b2485cfef17ed95a37707fcc1393e343e2d2ca11dabf",
    ),
    "solid-box-space-diagonal": (
        "49dfc211-0bca-4ca2-8d18-27e2ed416906",
        (("image_1", "49dfc211-0bca-4ca2-8d18-27e2ed416906"),),
        "2f91867badade5f9a572245918c36362de35026d5e030546d6279f212177507a",
    ),
}

SOURCES = {
    "f4689cbc-e217-4787-85bf-30a406dc5ce7": (
        "f4689cbc-e217-4787-85bf-30a406dc5ce7",
        "faf11c1116dfb6cf1b8e7aadd7e61ac19ea0ed7acef33ab40be3bb60aa62da30",
    ),
    "626ee550-5e35-469c-b555-65cb5466e6ea": (
        "626ee550-5e35-469c-b555-65cb5466e6ea",
        "c77c16674e413e2be8fd86d8c60041474a2259604b5080f98b897d68d80a0582",
    ),
    "35f32791-9902-43fa-aa56-13a3e102c866": (
        "35f32791-9902-43fa-aa56-13a3e102c866",
        "56e2bf655f30292b5e8d36a8bfa7dcfa2ce96f0a9ca65d87fc31edd84036492c",
    ),
    "847dce6a-d2ff-4246-90e6-3d38d7490edd": (
        "847dce6a-d2ff-4246-90e6-3d38d7490edd",
        "607f6ca2e726ed87180698040256bfaeaff50640a99588fe3fefef5dc524b03b",
    ),
    "6c17c081-08ea-43fa-9da5-5fb7a08387a2": (
        "6c17c081-08ea-43fa-9da5-5fb7a08387a2",
        "15d3f02bc6e5b4cbf2e888be67f766b57e461aa0ee14bd9f3f80b55d61dc1bfa",
    ),
    "66d11cfd-6c56-4268-8b85-6e4549417bbe": (
        "66d11cfd-6c56-4268-8b85-6e4549417bbe",
        "4126497750f71a0d8db76022529d443415fbb210f6324e2d7fb5a6d40b8435eb",
    ),
    "06ddc2e1-f28f-494f-90d6-8d5416fb8074": (
        "06ddc2e1-f28f-494f-90d6-8d5416fb8074",
        "1b2ffd67e837c155cb2873eb0f6dc3d7355dabada23001672e81f61b48d3ab72",
    ),
    "672a8a89-3d45-4a1f-ada8-ddf91e3f5582": (
        "672a8a89-3d45-4a1f-ada8-ddf91e3f5582",
        "8e07e15711d9d8f7353e8fe9a333f86666049bbcb10a78d4743bc3ec1c7537ff",
    ),
    "e8daeb88-d29f-4113-8de3-1bbe5e85bb48": (
        "e8daeb88-d29f-4113-8de3-1bbe5e85bb48",
        "aac04d85e4e08a04bbdc4e4928407a0f6acca25640de0e3ea895bcad6906012d",
    ),
    "3b5beb4c-37be-486d-87d1-ac7acf2b0020": (
        "3b5beb4c-37be-486d-87d1-ac7acf2b0020",
        "1756d7980f80f84ce64623b50db25fe31db620cc8e826295809b61f9d7db8515",
    ),
    "fb5c19ca-f54c-4e55-8078-2cfd9fad071c": (
        "fb5c19ca-f54c-4e55-8078-2cfd9fad071c",
        "606675e62c9e51d2ed39773f4d5d5fb62ab40f1fb6fc7b65bd0f2056ef394876",
    ),
    "e59f74ba-f7f9-469f-927c-01c7dc3dee63": (
        "e59f74ba-f7f9-469f-927c-01c7dc3dee63",
        "e9e65fc95c3531ee40d89a2731129ed236c3fa5d113a4e13eeac8bc32f28379c",
    ),
    "3307805d-1dcf-45fd-9625-17b4078991fd": (
        "3307805d-1dcf-45fd-9625-17b4078991fd",
        "cf9bf340665b80e709d965b51ebaa6b539c8f56b1f5d82e3460f0f6146d1d789",
    ),
    "462365c6-6627-4129-8a3e-3b1cddbfd4d6": (
        "462365c6-6627-4129-8a3e-3b1cddbfd4d6",
        "98c8a9abf3a49ae764a66a5a760ff9dfb393f19e54e993e0f7d686e2b166a498",
    ),
    "49dfc211-0bca-4ca2-8d18-27e2ed416906": (
        "49dfc211-0bca-4ca2-8d18-27e2ed416906",
        "a5abe23b07746d68e7fe3441afbd40cad02b71b8775790e9fa7a0107fe37229a",
    ),
}

MODE_SOURCES = {
    "distance_squared": (
        "35f32791-9902-43fa-aa56-13a3e102c866",
        "626ee550-5e35-469c-b555-65cb5466e6ea",
        "847dce6a-d2ff-4246-90e6-3d38d7490edd",
        "f4689cbc-e217-4787-85bf-30a406dc5ce7",
    ),
    "distance": (
        "06ddc2e1-f28f-494f-90d6-8d5416fb8074",
        "66d11cfd-6c56-4268-8b85-6e4549417bbe",
        "672a8a89-3d45-4a1f-ada8-ddf91e3f5582",
        "6c17c081-08ea-43fa-9da5-5fb7a08387a2",
    ),
    "edge": (
        "3307805d-1dcf-45fd-9625-17b4078991fd",
        "3b5beb4c-37be-486d-87d1-ac7acf2b0020",
        "462365c6-6627-4129-8a3e-3b1cddbfd4d6",
        "e59f74ba-f7f9-469f-927c-01c7dc3dee63",
        "e8daeb88-d29f-4113-8de3-1bbe5e85bb48",
        "fb5c19ca-f54c-4e55-8078-2cfd9fad071c",
    ),
    "diagonal": ("49dfc211-0bca-4ca2-8d18-27e2ed416906",),
}

FIGURES = {
    "f4689cbc-e217-4787-85bf-30a406dc5ce7": {
        "dimensions": ("25", "16", "9"),
        "blue": (),
    },
    "626ee550-5e35-469c-b555-65cb5466e6ea": {
        "dimensions": ("25", "16", "9"),
        "blue": (("A", "A_1"), ("A", "C"), ("A_1", "C")),
    },
    "35f32791-9902-43fa-aa56-13a3e102c866": {
        "dimensions": ("25", "25", "9"),
        "blue": (),
    },
    "847dce6a-d2ff-4246-90e6-3d38d7490edd": {
        "dimensions": ("25", "25", "9"),
        "blue": (("B", "D"), ("D", "D_1"), ("B", "D_1")),
    },
    "6c17c081-08ea-43fa-9da5-5fb7a08387a2": {
        "dimensions": ("25", "16", "9"),
        "blue": (),
    },
    "66d11cfd-6c56-4268-8b85-6e4549417bbe": {
        "dimensions": ("25", "16", "9"),
        "blue": (("A", "D"), ("A", "A_1"), ("A_1", "D_1"), ("D", "D_1"), ("A", "D_1")),
    },
    "06ddc2e1-f28f-494f-90d6-8d5416fb8074": {
        "dimensions": ("144", "49", "25"),
        "blue": (),
    },
    "672a8a89-3d45-4a1f-ada8-ddf91e3f5582": {
        "dimensions": ("144", "49", "25"),
        "blue": (("A", "B"), ("A", "A_1"), ("A_1", "B")),
    },
    "e8daeb88-d29f-4113-8de3-1bbe5e85bb48": {
        "dimensions": None,
        "blue": (("B", "D"), ("B", "D_1")),
    },
    "3b5beb4c-37be-486d-87d1-ac7acf2b0020": {
        "dimensions": None,
        "blue": (("B", "D_1"),),
    },
    "fb5c19ca-f54c-4e55-8078-2cfd9fad071c": {
        "dimensions": None,
        "blue": (("A", "D_1"), ("B", "D_1")),
    },
    "e59f74ba-f7f9-469f-927c-01c7dc3dee63": {"dimensions": None, "blue": ()},
    "3307805d-1dcf-45fd-9625-17b4078991fd": {
        "dimensions": None,
        "blue": (("A", "D_1"), ("B", "D_1")),
    },
    "462365c6-6627-4129-8a3e-3b1cddbfd4d6": {"dimensions": None, "blue": ()},
    "49dfc211-0bca-4ca2-8d18-27e2ed416906": {
        "dimensions": None,
        "blue": (("A", "C"), ("A_1", "C")),
    },
}


def source_bytes(source):
    from . import source_assets

    return source_assets.source_bytes(source, SOURCES)


def review_parent(rule, primary, html, assets):
    from . import source_assets

    return source_assets.review_parent(
        rule, primary, html, assets, parents=PARENTS, sources=SOURCES
    )
