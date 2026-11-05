"""Pin complete sphere parents and exact compatible SVG/PNG source identities."""

from . import source_assets

PARENTS = {
    "solid-sphere-great-circle-surface": (
        "d95b4646-f780-4918-a15e-d51589cb18c4",
        (),
        "a8a321af21000d8ffe8f7d000e777a7d73602aac05530b867602d994e149d29d",
    ),
    "solid-sphere-surface-from-radius-ratio": (
        "1f9a7a72-15ca-4ec5-856e-88f6ad7c7f65",
        (),
        "b185fe73e72ee682826a482127170db825d915203a163ad743bd7dc1d7572e0e",
    ),
    "solid-sphere-volume-factor": (
        "ef77deff-825b-435b-a9f9-3a5f5cbc3a5d",
        (),
        "7363f40948f3abd3d1ff5097a49ae65d8e14c088124b6aceaf07ae73bf5616d1",
    ),
    "solid-sphere-sum-volumes-radius": (
        None,
        (),
        "357bc85ca04b05a15808aae47be6f21649f88d0479b90fecaafa681e9c9250d2",
    ),
    "solid-sphere-surface-from-volume-ratio": (
        "1f9a7a72-15ca-4ec5-856e-88f6ad7c7f65",
        (),
        "ffd353627b04b5a99f54a9e781bb9d2f4cf590dcf3f89b710ec6b426c311513b",
    ),
    "solid-sphere-sum-surfaces-radius": (
        "f8eb4e81-eee1-450b-a1c5-330b78ebb1fd",
        (),
        "ac54e79f77418e97c7ac2e7bda567e794212be05b73341c01590e8bfb874e101",
    ),
    "solid-sphere-surface-from-pi-volume": (
        "ef77deff-825b-435b-a9f9-3a5f5cbc3a5d",
        (),
        "e6761a94d92ceb5c7dab0814cfe4f66bd3318c765edd09b29e16c585c782056f",
    ),
}
RULES = {
    "solid-sphere-great-circle-surface": "great_circle_surface",
    "solid-sphere-surface-from-radius-ratio": "surface_factor",
    "solid-sphere-volume-factor": "volume_factor",
    "solid-sphere-sum-volumes-radius": "combined_radius_volume",
    "solid-sphere-surface-from-volume-ratio": "surface_factor",
    "solid-sphere-sum-surfaces-radius": "combined_radius_area",
    "solid-sphere-surface-from-pi-volume": "surface_over_pi",
}
SOURCES = {
    "1f9a7a72-15ca-4ec5-856e-88f6ad7c7f65": (
        "1f9a7a72-15ca-4ec5-856e-88f6ad7c7f65",
        "8296981046b6909e8180590c380421515040ee706cb1a3f9c39841bff96ed1e2",
    ),
    "d95b4646-f780-4918-a15e-d51589cb18c4": (
        "d95b4646-f780-4918-a15e-d51589cb18c4",
        "170592d82ad35e4516882e18210443cb5528726976049c8d44f105a991ea291b",
    ),
    "14103aaf-178e-4060-b49c-dadde8b6f6b5": (
        "14103aaf-178e-4060-b49c-dadde8b6f6b5.png",
        "19363e76bbe32e6105542798cd4e95de3a7645418dc037c2fde0e2f742c82468",
    ),
    "ef77deff-825b-435b-a9f9-3a5f5cbc3a5d": (
        "ef77deff-825b-435b-a9f9-3a5f5cbc3a5d",
        "2dd515e95349c22e0873ae1692ffe140bc5240616ada9749a9008b50aaa0374a",
    ),
    "f8eb4e81-eee1-450b-a1c5-330b78ebb1fd": (
        "f8eb4e81-eee1-450b-a1c5-330b78ebb1fd",
        "3bf523f235ecfb3b5f2c81bfadb51a6ce24110ebcb793e4ab0bdff95b27c28e7",
    ),
}
MODE_SOURCES = {
    "great_circle_surface": ("d95b4646-f780-4918-a15e-d51589cb18c4",),
    "surface_factor": ("1f9a7a72-15ca-4ec5-856e-88f6ad7c7f65",),
    "volume_factor": ("ef77deff-825b-435b-a9f9-3a5f5cbc3a5d",),
    "combined_radius_volume": (),
    "combined_radius_area": (
        "f8eb4e81-eee1-450b-a1c5-330b78ebb1fd",
        "14103aaf-178e-4060-b49c-dadde8b6f6b5",
    ),
    "surface_over_pi": ("ef77deff-825b-435b-a9f9-3a5f5cbc3a5d",),
}


def source_bytes(source):
    return source_assets.source_bytes(source, SOURCES)


def review_parent(rule, primary, html, assets):
    return source_assets.review_parent(
        rule, primary, html, assets, parents=PARENTS, sources=SOURCES
    )
