"""Reviewed box parent methods and exact compatible source identities."""

RULES = {
    "solid-box-edge-from-surface": "edge_from_surface",
    "solid-box-diagonal-from-surface": "diagonal_from_surface",
    "solid-box-volume-from-face": "volume_from_face",
    "solid-box-face-from-volume": "face_from_volume",
    "solid-box-edge-from-face": "edge_from_face",
    "solid-box-edge-from-volume": "edge_from_volume",
    "solid-box-cube-edge-from-edges": "cube_edge_from_edges",
    "solid-box-volume-from-diagonal": "volume_from_diagonal",
    "solid-box-diagonal-from-volume": "diagonal_from_volume",
    "solid-box-surface-from-edges": "surface_from_edges",
    "solid-box-surface-from-diagonal": "surface_from_diagonal",
    "solid-box-surface-from-volume": "surface_from_volume",
}

PARENTS = {
    "solid-box-edge-from-surface": (
        "74132896-50ea-4371-9de4-f847a4e7e7e3",
        (),
        "7774f7a48d7d6b4c1857fa8ba291a7e4828bb468d640a10cab3c0e873b8e1a50",
    ),
    "solid-box-diagonal-from-surface": (
        "44453f36-8974-46ba-81bd-2827592b6c79",
        (),
        "311dfe6b131ad1e7522dffe1f0f38469829f51fd1d9c61e64ce043de6fc44f58",
    ),
    "solid-box-volume-from-face": (
        "6831a422-8bcf-403c-87ed-9ee5dba5266b",
        (),
        "b7a6fd2902af0667298e1aeac75d5e249c637769a626ba0e452f56c76026179b",
    ),
    "solid-box-face-from-volume": (
        "e4996d20-4f3b-47f6-bd14-b52a4d9764bc",
        (),
        "444dab289856a027a3b14a90c8a609720172c3f9b6ca025aefaa346639dd1f5e",
    ),
    "solid-box-edge-from-face": (
        "e859282e-d8c1-449a-97b9-c522e570aab0",
        (),
        "0a7c2111a2b08ea1df1b890ff020b68054bcaca187b8cace37f5a029314839c5",
    ),
    "solid-box-edge-from-volume": (
        "38163517-0b46-463f-8564-041e390c6949",
        (),
        "f311e43b74d71d4025681c37ebdebd8e7b5c810f92cf3d5b59173710ca6d3f99",
    ),
    "solid-box-cube-edge-from-edges": (
        "deecd2cd-ac2d-47f0-b4f0-1383038e868e",
        (),
        "0ffad4c03516a379fa5b9c4c0854807fd9a34d6c2f943e46587ae58d448a17cc",
    ),
    "solid-box-volume-from-diagonal": (
        "44453f36-8974-46ba-81bd-2827592b6c79",
        (),
        "2f39274b1a8db3a35e8633e1eeb3e5b5e769291f124b600c44b6407de60fffd8",
    ),
    "solid-box-diagonal-from-volume": (
        "44453f36-8974-46ba-81bd-2827592b6c79",
        (),
        "81c447aeb07f0d5b724c731b9484203c15174d275a3741171239ff546e6ae725",
    ),
    "solid-box-surface-from-edges": (
        "deecd2cd-ac2d-47f0-b4f0-1383038e868e",
        (),
        "1a1affc7b97effc2bf71725c2de9ad3e60ea3e0193aff152406ca96d800432a4",
    ),
    "solid-box-surface-from-diagonal": (
        "44453f36-8974-46ba-81bd-2827592b6c79",
        (),
        "edf8ccf3acb26a850aac56aa06a84945a51a8653250d088f5634690ebd24d6b0",
    ),
    "solid-box-surface-from-volume": (
        "deecd2cd-ac2d-47f0-b4f0-1383038e868e",
        (),
        "f589aee000c4b966c41d93c4a4dce3b650ab79f8382522efbc04f3f76745d0df",
    ),
}

SOURCES = {
    "3326ee19-f100-4c04-b129-4692f18629a1": (
        "3326ee19-f100-4c04-b129-4692f18629a1",
        "571239ab73c062c246fb2cb27a564a54184b298276f928caf089d80b91ceb303",
    ),
    "38163517-0b46-463f-8564-041e390c6949": (
        "3326ee19-f100-4c04-b129-4692f18629a1",
        "571239ab73c062c246fb2cb27a564a54184b298276f928caf089d80b91ceb303",
    ),
    "44453f36-8974-46ba-81bd-2827592b6c79": (
        "44453f36-8974-46ba-81bd-2827592b6c79",
        "310712236cd99ba7ad04860051c472381439efc3f73a40764cffdb772676d030",
    ),
    "6831a422-8bcf-403c-87ed-9ee5dba5266b": (
        "3326ee19-f100-4c04-b129-4692f18629a1",
        "571239ab73c062c246fb2cb27a564a54184b298276f928caf089d80b91ceb303",
    ),
    "69ddb87a-ec3d-447d-b349-2f184f5c2e3e": (
        "69ddb87a-ec3d-447d-b349-2f184f5c2e3e",
        "203ae125b53444ed0a44eaed2489b3f1da63174bd6e17470e08b9ffc23f973ff",
    ),
    "74132896-50ea-4371-9de4-f847a4e7e7e3": (
        "3326ee19-f100-4c04-b129-4692f18629a1",
        "571239ab73c062c246fb2cb27a564a54184b298276f928caf089d80b91ceb303",
    ),
    "8356c31e-6a73-44ad-b1c5-7e447bf53ca3": (
        "69ddb87a-ec3d-447d-b349-2f184f5c2e3e",
        "203ae125b53444ed0a44eaed2489b3f1da63174bd6e17470e08b9ffc23f973ff",
    ),
    "b426d494-ac99-4feb-b638-82bcf705eb18": (
        "69ddb87a-ec3d-447d-b349-2f184f5c2e3e",
        "203ae125b53444ed0a44eaed2489b3f1da63174bd6e17470e08b9ffc23f973ff",
    ),
    "deecd2cd-ac2d-47f0-b4f0-1383038e868e": (
        "3326ee19-f100-4c04-b129-4692f18629a1",
        "571239ab73c062c246fb2cb27a564a54184b298276f928caf089d80b91ceb303",
    ),
    "e183a5fd-cb0b-491b-bc71-9b2ef83eebca": (
        "69ddb87a-ec3d-447d-b349-2f184f5c2e3e",
        "203ae125b53444ed0a44eaed2489b3f1da63174bd6e17470e08b9ffc23f973ff",
    ),
    "e4996d20-4f3b-47f6-bd14-b52a4d9764bc": (
        "3326ee19-f100-4c04-b129-4692f18629a1",
        "571239ab73c062c246fb2cb27a564a54184b298276f928caf089d80b91ceb303",
    ),
    "e859282e-d8c1-449a-97b9-c522e570aab0": (
        "3326ee19-f100-4c04-b129-4692f18629a1",
        "571239ab73c062c246fb2cb27a564a54184b298276f928caf089d80b91ceb303",
    ),
    "f763de8e-a794-4229-a266-3fee73c52456": (
        "69ddb87a-ec3d-447d-b349-2f184f5c2e3e",
        "203ae125b53444ed0a44eaed2489b3f1da63174bd6e17470e08b9ffc23f973ff",
    ),
}

BARE_SOURCES = (
    "3326ee19-f100-4c04-b129-4692f18629a1",
    "38163517-0b46-463f-8564-041e390c6949",
    "6831a422-8bcf-403c-87ed-9ee5dba5266b",
    "69ddb87a-ec3d-447d-b349-2f184f5c2e3e",
    "74132896-50ea-4371-9de4-f847a4e7e7e3",
    "8356c31e-6a73-44ad-b1c5-7e447bf53ca3",
    "b426d494-ac99-4feb-b638-82bcf705eb18",
    "deecd2cd-ac2d-47f0-b4f0-1383038e868e",
    "e183a5fd-cb0b-491b-bc71-9b2ef83eebca",
    "e4996d20-4f3b-47f6-bd14-b52a4d9764bc",
    "e859282e-d8c1-449a-97b9-c522e570aab0",
    "f763de8e-a794-4229-a266-3fee73c52456",
)
DIAGONAL_SOURCES = ("44453f36-8974-46ba-81bd-2827592b6c79",)
MODE_SOURCES = {
    "edge_from_surface": BARE_SOURCES,
    "diagonal_from_surface": DIAGONAL_SOURCES,
    "volume_from_face": BARE_SOURCES,
    "face_from_volume": BARE_SOURCES,
    "edge_from_face": BARE_SOURCES,
    "edge_from_volume": BARE_SOURCES,
    "cube_edge_from_edges": BARE_SOURCES,
    "volume_from_diagonal": DIAGONAL_SOURCES,
    "diagonal_from_volume": DIAGONAL_SOURCES,
    "surface_from_edges": BARE_SOURCES,
    "surface_from_diagonal": DIAGONAL_SOURCES,
    "surface_from_volume": BARE_SOURCES,
}


def source_bytes(source):
    from . import source_assets

    return source_assets.source_bytes(source, SOURCES)


def review_parent(rule, primary, html, assets):
    from . import source_assets

    return source_assets.review_parent(
        rule, primary, html, assets, parents=PARENTS, sources=SOURCES
    )
