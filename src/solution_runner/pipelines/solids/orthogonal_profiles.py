"""Explicit bindings for reviewed orthogonal-polyhedron volume methods."""

from ..core.profile_definitions import _profile
from .orthogonal_element_profiles import PROFILES as ELEMENT_PROFILES
from .orthogonal_surface_profiles import PROFILES as SURFACE_PROFILES

PROFILES = tuple(
    _profile(
        key,
        uid,
        index,
        catalog_snapshot_id="41bc4d03-40cd-4407-8dea-df76e3f47ea8",
        category_key="3",
        theme_title="Объем составного многогранника",
        theme_order_index=4,
        snapshot_theme_id="e49830bc-246a-47a3-b57d-eef2ee599f76",
        expected_vertices=None,
        strategy_key=None,
        workflow_kind="content_rule",
        content_rule_key=rule,
        rewrite_existing_solution=True,
    )
    for key, uid, index, rule in (
        (
            "27044",
            "18002efb-58e7-4129-8108-647de550d1a2",
            0,
            "solid-orthogonal-volume-step-width",
        ),
        (
            "27187",
            "951e6ad5-cc02-4ab0-9ae2-df77914058dd",
            2,
            "solid-orthogonal-volume-step-rise",
        ),
        (
            "27188",
            "88fe3c54-e6e5-42a3-a1c7-03fb9788dea1",
            3,
            "solid-orthogonal-volume-depth-step",
        ),
        (
            "27189",
            "38aee4a5-eaf6-4edd-842f-b1a7712b9160",
            4,
            "solid-orthogonal-volume-plan-step",
        ),
        (
            "27190",
            "a65122d3-fbff-43d3-acf6-0dd2e03271af",
            5,
            "solid-orthogonal-volume-upper-corner-left",
        ),
        (
            "27191",
            "90fd6683-e54d-48de-ba48-888df8507368",
            6,
            "solid-orthogonal-volume-front-notch",
        ),
        (
            "27192",
            "8bc36e83-97e5-4085-bb5e-cc6dee5f67ca",
            7,
            "solid-orthogonal-volume-front-groove",
        ),
        (
            "27193",
            "df53a9be-37e7-4e09-b586-5ae39ed6ba5f",
            8,
            "solid-orthogonal-volume-bar",
        ),
        (
            "27194",
            "cfccfd1c-3daa-4835-b122-bf8ab2faf0ee",
            9,
            "solid-orthogonal-volume-shelf",
        ),
        (
            "27195",
            "b13b4daa-7943-4ef1-8e40-b00195f615a3",
            10,
            "solid-orthogonal-volume-through-plate",
        ),
        (
            "27210",
            "f5463565-d235-4ae1-a81d-23eb683ceb61",
            11,
            "solid-orthogonal-volume-pedestal",
        ),
        (
            "27211",
            "fef6f233-ce26-4535-bcff-283dc32d20b1",
            12,
            "solid-orthogonal-volume-side-boxes",
        ),
        (
            "27212",
            "e168ce46-b381-4306-bc62-ddf9f70a3dd8",
            13,
            "solid-orthogonal-volume-right-wing",
        ),
        (
            "27213",
            "078ebf6f-7a1b-4eb5-bbf4-d6698cc2356e",
            14,
            "solid-orthogonal-volume-left-wing",
        ),
        (
            "27216",
            "ab3d79fe-9d17-4dbf-9d20-5f94980ab647",
            15,
            "solid-orthogonal-volume-upper-corner-right",
        ),
    )
)


PROFILES += SURFACE_PROFILES
PROFILES += ELEMENT_PROFILES
