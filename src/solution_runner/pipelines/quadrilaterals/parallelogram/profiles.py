"""Parallelogram groups bound to their reviewed parent methods."""

from solution_runner.pipelines.core.profile_definitions import _profile

from .midpoint_model import HEIGHT, PERIMETER, TWO_TRAPEZOID, TWO_TRIANGLE, VARIGNON

PROFILES = tuple(
    _profile(
        key,
        identifier,
        index,
        catalog_snapshot_id="41bc4d03-40cd-4407-8dea-df76e3f47ea8",
        category_key="1",
        theme_title="Параллелограммы",
        theme_order_index=3,
        snapshot_theme_id="b83f22cf-01ea-4a6e-802d-0a2a1831924e",
        expected_vertices=None,
        strategy_key=None,
        workflow_kind="content_rule",
        content_rule_key=rule,
        rewrite_existing_solution=True,
    )
    for key, identifier, index, rule in (
        ("27845", "0638b40d-6f64-4dfc-8398-d598e5334386", 27, PERIMETER),
        ("317338", "07a0cb21-4434-46af-b91b-112adf950a2a", 30, TWO_TRAPEZOID),
        ("319056", "acad8e12-9935-4d79-9a1f-3aface7f792a", 31, VARIGNON),
        ("319057", "10245d06-828f-44a3-a575-e92fef7a32fc", 32, TWO_TRIANGLE),
        ("665285", "f43579ce-3c4e-4b2e-97a0-cab36f034bef", 34, HEIGHT),
    )
)
