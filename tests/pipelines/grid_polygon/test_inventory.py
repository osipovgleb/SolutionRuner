"""Verify read-only inventory classification from normalized asset identities."""

from __future__ import annotations

import threading
from typing import Any

from solution_runner.pipelines.grid_polygon.group_profiles import get_group_profile
from solution_runner.pipelines.grid_polygon.inventory import discover_group_inventory


class InventoryGateway:
    """Return one real-shaped SVG target whose normalized asset omits MIME data."""

    def get_source_catalog_children(
        self,
        parent_id: str,
        parent_type: str,
    ) -> dict[str, Any]:
        """Return the exact prototype membership identity."""

        assert parent_id == "a3e9590e-400a-4e2e-9fcc-a4ddc94e53ab"
        assert parent_type == "group"
        return {
            "items": [
                {
                    "name": "Задача 244982",
                    "uuid": "70577c0a-c9ea-4530-bd85-47139f25eaf8",
                }
            ]
        }

    def get_problem_pipeline_state(self, problem_id: str) -> dict[str, Any]:
        """Expose one eligible normalized target."""

        assert problem_id == "70577c0a-c9ea-4530-bd85-47139f25eaf8"
        return {"statuses": {"normalized": "ready"}}

    def get_source_catalog_section_images(self, target_id: str, target_type: str):
        """Return the current condition occurrence while omitting its MIME type."""

        return {
            "condition": {
                "problem_count": 1,
                "problems": [
                    {
                        "source_problem_id": "244982",
                        "images": [
                            {
                                "asset_key": "image_1",
                                "asset_id": "1d877c7e-d587-4bec-8315-c501fa6e03f2",
                                "kind": "ordinary_image",
                                "content_type": None,
                            }
                        ],
                    }
                ],
            },
            "solution": {"problem_count": 0, "problems": []},
        }

    def get_source_catalog_missing_solution_summary(
        self,
        target_id: str,
        target_type: str,
    ):
        """Return no missing solutions for this all-scope profile fixture."""

        return {"concrete_problem_count": 1, "count": 0, "source_problem_ids": []}

    def get_problem_context(self, problem_id: str) -> dict[str, Any]:
        """Mirror normalized content, where the asset URL carries no extension."""

        assert problem_id == "70577c0a-c9ea-4530-bd85-47139f25eaf8"
        return {
            "normalized_content": {
                "assets": [
                    {
                        "asset_key": "image_1",
                        "kind": "ordinary_image",
                        "asset_id": "1d877c7e-d587-4bec-8315-c501fa6e03f2",
                        "url": "/assets/1d877c7e-d587-4bec-8315-c501fa6e03f2",
                        "alt": "",
                    }
                ]
            }
        }

    def get_asset_metadata(self, asset_id: str) -> dict[str, Any]:
        """Return the authoritative MIME type from the asset read boundary."""

        assert asset_id == "1d877c7e-d587-4bec-8315-c501fa6e03f2"
        return {
            "asset_id": asset_id,
            "content_type": "image/svg+xml",
        }


class BmpInventoryGateway:
    """Return the real BMP condition shape used by source problem 71887."""

    def get_source_catalog_children(
        self,
        parent_id: str,
        parent_type: str,
    ) -> dict[str, Any]:
        """Return only the audited BMP target in group 27553."""

        assert parent_id == "0efa9c9d-8b0a-4eda-8f91-3bab53034f85"
        assert parent_type == "group"
        return {"items": [{"name": "Задача 71887", "uuid": "problem-71887"}]}

    def get_problem_pipeline_state(self, problem_id: str) -> dict[str, Any]:
        """Expose the BMP target as eligible normalized content."""

        assert problem_id == "problem-71887"
        return {"statuses": {"normalized": "ready"}}

    def get_source_catalog_section_images(self, target_id: str, target_type: str):
        """Return one current BMP condition occurrence."""

        return {
            "condition": {
                "problem_count": 1,
                "problems": [
                    {
                        "source_problem_id": "71887",
                        "images": [
                            {
                                "asset_key": "image_1",
                                "asset_id": "bmp-asset",
                                "kind": "ordinary_image",
                                "content_type": "image/bmp",
                            }
                        ],
                    }
                ],
            },
            "solution": {"problem_count": 0, "problems": []},
        }

    def get_source_catalog_missing_solution_summary(
        self,
        target_id: str,
        target_type: str,
    ):
        """Return no missing solutions for this all-scope profile fixture."""

        return {"concrete_problem_count": 1, "count": 0, "source_problem_ids": []}

    def get_problem_context(self, problem_id: str) -> dict[str, Any]:
        """Return the authoritative BMP MIME type on the current asset."""

        assert problem_id == "problem-71887"
        return {
            "normalized_content": {
                "assets": [
                    {
                        "asset_key": "image_1",
                        "kind": "ordinary_image",
                        "asset_id": "bmp-asset",
                        "content_type": "image/bmp",
                    }
                ]
            }
        }

    def get_asset_metadata(self, asset_id: str) -> dict[str, Any]:
        """Fail if inventory needlessly rereads metadata already present."""

        raise AssertionError(f"unexpected metadata read for {asset_id}")


def test_inventory_resolves_missing_normalized_content_type_from_asset_metadata() -> None:
    """Classify the legacy prototype as SVG without guessing from its UUID URL."""

    inventory = discover_group_inventory(
        InventoryGateway(),
        get_group_profile("244982"),
    )

    assert [target.source_problem_id for target in inventory.targets] == ["244982"]
    assert inventory.png_targets == ()
    assert [target.source_problem_id for target in inventory.svg_targets] == [
        "244982"
    ]


def test_inventory_routes_bmp_through_the_raster_conversion_bucket() -> None:
    """Keep source problem 71887 eligible for the shared raster converter."""

    inventory = discover_group_inventory(
        BmpInventoryGateway(),
        get_group_profile("27553"),
    )

    assert [target.source_problem_id for target in inventory.targets] == ["71887"]
    assert [target.source_problem_id for target in inventory.png_targets] == ["71887"]
    assert inventory.svg_targets == ()


class ContentRuleInventoryGateway:
    """Expose image-free and rejected tasks in one content-only group."""

    def get_source_catalog_children(self, parent_id: str, parent_type: str):
        """Return all tasks in their source order."""

        assert (parent_id, parent_type) == (
            "8b5a2cb7-4831-4355-9d47-e473b8aef65c",
            "group",
        )
        return {
            "items": [
                {"name": "Задача 27238", "uuid": "problem-parent"},
                {"name": "Задача 4583", "uuid": "problem-no-image"},
                {"name": "Задача 4636", "uuid": "problem-rejected"},
            ]
        }

    def get_problem_pipeline_state(self, problem_id: str):
        """Keep ready tasks and exclude the rejected child."""

        return {
            "statuses": {
                "normalized": (
                    "rejected" if problem_id == "problem-rejected" else "ready"
                )
            }
        }

    def get_source_catalog_section_images(self, target_id: str, target_type: str):
        """Show that only the first task currently has a condition image."""

        return {
            "condition": {
                "problem_count": 1,
                "problems": [
                    {
                        "source_problem_id": "27238",
                        "images": [
                            {
                                "asset_key": "image_1",
                                "asset_id": "parent-asset",
                                "kind": "ordinary_image",
                                "content_type": "image/svg+xml",
                            }
                        ],
                    }
                ],
            },
            "solution": {"problem_count": 0, "problems": []},
        }

    def get_source_catalog_missing_solution_summary(
        self, target_id: str, target_type: str
    ):
        """Return a valid audit whose filtering must not narrow content rules."""

        return {
            "concrete_problem_count": 3,
            "count": 1,
            "source_problem_ids": ["4583"],
        }

    def get_asset_metadata(self, asset_id: str):
        """Fail because content workflows do not classify image formats."""

        raise AssertionError(f"unexpected asset metadata read for {asset_id}")


def test_content_rule_inventory_includes_ready_tasks_without_current_images() -> None:
    """Supply image repairs to every ready task while excluding rejected content."""

    inventory = discover_group_inventory(
        ContentRuleInventoryGateway(),
        get_group_profile("27238"),
        max_workers=3,
    )

    assert [target.source_problem_id for target in inventory.targets] == [
        "27238",
        "4583",
    ]
    assert inventory.png_targets == ()
    assert inventory.svg_targets == ()


class MissingSolutionInventoryGateway:
    """Expose one reference solution and one unsolved annulus child."""

    def get_source_catalog_children(self, parent_id: str, parent_type: str):
        """Return two ordered group members."""

        assert parent_id == "35a2b971-d6d3-4013-817b-5dd44a4e9c65"
        assert parent_type == "group"
        return {
            "items": [
                {"name": "Задача 245008", "uuid": "problem-parent"},
                {"name": "Задача 263425", "uuid": "problem-child"},
            ]
        }

    def get_problem_pipeline_state(self, problem_id: str):
        """Mark both problems eligible before solution-scope filtering."""

        return {"statuses": {"normalized": "ready"}}

    def get_source_catalog_section_images(self, target_id: str, target_type: str):
        """Return both current condition image occurrences."""

        return {
            "condition": {
                "problem_count": 2,
                "problems": [
                    {
                        "source_problem_id": source_problem_id,
                        "images": [
                            {
                                "asset_key": "image_1",
                                "asset_id": f"asset-problem-{kind}",
                                "kind": "ordinary_image",
                                "content_type": "image/png",
                            }
                        ],
                    }
                    for source_problem_id, kind in (
                        ("245008", "parent"),
                        ("263425", "child"),
                    )
                ],
            },
            "solution": {"problem_count": 0, "problems": []},
        }

    def get_source_catalog_missing_solution_summary(
        self,
        target_id: str,
        target_type: str,
    ):
        """Select only the unsolved child."""

        return {
            "concrete_problem_count": 2,
            "count": 1,
            "source_problem_ids": ["263425"],
        }

    def get_problem_context(self, problem_id: str):
        """Return an existing reference solution only for the parent."""

        sections = (
            [{"key": "solution", "html": "<p>Эталон</p>"}]
            if problem_id == "problem-parent"
            else []
        )
        return {
            "normalized_content": {
                "sections": sections,
                "assets": [
                    {
                        "asset_key": "image_1",
                        "kind": "ordinary_image",
                        "asset_id": f"asset-{problem_id}",
                        "content_type": "image/png",
                    }
                ],
            }
        }

    def get_asset_metadata(self, asset_id: str):
        """Fail because normalized content already includes MIME data."""

        raise AssertionError(f"unexpected metadata lookup for {asset_id}")


def test_missing_solution_scope_excludes_reference_problems() -> None:
    """Leave parent solutions, answers, assets, and Helpers outside the worklist."""

    inventory = discover_group_inventory(
        MissingSolutionInventoryGateway(),
        get_group_profile("245008"),
    )

    assert [target.source_problem_id for target in inventory.targets] == ["263425"]


class RerunnableAnnulusInventoryGateway(MissingSolutionInventoryGateway):
    """Expose a reference, a prior pipeline result, and one unsolved child."""

    def get_source_catalog_children(self, parent_id: str, parent_type: str):
        """Return three ordered group members."""

        assert parent_id == "35a2b971-d6d3-4013-817b-5dd44a4e9c65"
        assert parent_type == "group"
        return {
            "items": [
                {"name": "Задача 245008", "uuid": "problem-parent"},
                {"name": "Задача 263425", "uuid": "problem-generated"},
                {"name": "Задача 263427", "uuid": "problem-empty"},
            ]
        }

    def get_problem_context(self, problem_id: str):
        """Mark only one existing solution as generated by this pipeline."""

        solution_html = {
            "problem-parent": "<p>Эталонное решение</p>",
            "problem-generated": (
                '<img data-asset-key="generated_solution_diagram" '
                'src="/assets/generated"/><p>Старое решение pipeline</p>'
            ),
        }.get(problem_id, "")
        sections = (
            [{"key": "solution", "html": solution_html}]
            if solution_html
            else []
        )
        return {
            "normalized_content": {
                "sections": sections,
                "assets": [
                    {
                        "asset_key": "image_1",
                        "kind": "ordinary_image",
                        "asset_id": f"asset-{problem_id}",
                        "content_type": "image/svg+xml",
                    }
                ],
            }
        }

    def get_source_catalog_section_images(self, target_id: str, target_type: str):
        """Expose one pipeline-generated solution diagram beside three conditions."""

        return {
            "condition": {
                "problem_count": 3,
                "problems": [
                    {
                        "source_problem_id": source_problem_id,
                        "images": [
                            {
                                "asset_key": "image_1",
                                "asset_id": f"asset-{source_problem_id}",
                                "kind": "ordinary_image",
                                "content_type": "image/svg+xml",
                            }
                        ],
                    }
                    for source_problem_id in ("245008", "263425", "263427")
                ],
            },
            "solution": {
                "problem_count": 1,
                "problems": [
                    {
                        "source_problem_id": "263425",
                        "images": [
                            {
                                "asset_key": "generated_solution_diagram",
                                "asset_id": "asset-generated-solution",
                                "kind": "ordinary_image",
                                "content_type": "image/svg+xml",
                            }
                        ],
                    }
                ],
            },
        }

    def get_source_catalog_missing_solution_summary(
        self,
        target_id: str,
        target_type: str,
    ):
        """Select the empty child while audit imagery selects the generated child."""

        return {
            "concrete_problem_count": 3,
            "count": 1,
            "source_problem_ids": ["263427"],
        }


def test_annulus_rerun_includes_prior_pipeline_solution_but_not_reference() -> None:
    """Rebuild generated children while leaving genuine reference HTML untouched."""

    inventory = discover_group_inventory(
        RerunnableAnnulusInventoryGateway(),
        get_group_profile("245008"),
    )

    assert [target.source_problem_id for target in inventory.targets] == [
        "263425",
        "263427",
    ]


class ConcurrentInventoryGateway:
    """Expose two SVG children and record overlapping state reads."""

    def __init__(self) -> None:
        """Create synchronization state for a deterministic overlap check."""

        self._lock = threading.Lock()
        self._second_entered = threading.Event()
        self._active = 0
        self.max_active = 0

    def get_source_catalog_children(self, parent_id: str, parent_type: str):
        """Return two ordered target identities."""

        return {
            "items": [
                {"name": "Задача 1", "uuid": "problem-1"},
                {"name": "Задача 2", "uuid": "problem-2"},
            ]
        }

    def get_problem_pipeline_state(self, problem_id: str):
        """Hold the first read briefly so a second worker can overlap it."""

        with self._lock:
            self._active += 1
            self.max_active = max(self.max_active, self._active)
            if self._active == 2:
                self._second_entered.set()
        self._second_entered.wait(timeout=0.2)
        with self._lock:
            self._active -= 1
        return {"statuses": {"normalized": "ready"}}

    def get_source_catalog_section_images(self, target_id: str, target_type: str):
        """Return both current SVG condition occurrences."""

        return {
            "condition": {
                "problem_count": 2,
                "problems": [
                    {
                        "source_problem_id": source_problem_id,
                        "images": [
                            {
                                "asset_key": "image_1",
                                "asset_id": f"asset-problem-{source_problem_id}",
                                "kind": "ordinary_image",
                                "content_type": "image/svg+xml",
                            }
                        ],
                    }
                    for source_problem_id in ("1", "2")
                ],
            },
            "solution": {"problem_count": 0, "problems": []},
        }

    def get_source_catalog_missing_solution_summary(
        self,
        target_id: str,
        target_type: str,
    ):
        """Return no missing solutions for this all-scope profile fixture."""

        return {"concrete_problem_count": 2, "count": 0, "source_problem_ids": []}

    def get_problem_context(self, problem_id: str):
        """Return one complete current SVG asset."""

        return {
            "normalized_content": {
                "assets": [
                    {
                        "asset_key": "image_1",
                        "kind": "ordinary_image",
                        "asset_id": f"asset-{problem_id}",
                        "content_type": "image/svg+xml",
                    }
                ]
            }
        }

    def get_asset_metadata(self, asset_id: str):
        """Reject an unnecessary metadata lookup."""

        raise AssertionError(f"unexpected metadata lookup for {asset_id}")


def test_inventory_workers_overlap_children_and_preserve_source_order() -> None:
    """Parallelize independent reads while retaining catalog order."""

    gateway = ConcurrentInventoryGateway()
    inventory = discover_group_inventory(
        gateway,
        get_group_profile("244982"),
        max_workers=2,
    )

    assert gateway.max_active == 2
    assert [target.source_problem_id for target in inventory.targets] == ["1", "2"]


class AuditInventoryGateway:
    """Expose compact group audits and reject legacy per-problem content reads."""

    def __init__(self) -> None:
        """Create a barrier proving the three independent audit reads overlap."""

        self._barrier = threading.Barrier(3)
        self._lock = threading.Lock()
        self._active = 0
        self.max_active = 0
        self.state_problem_ids: list[str] = []

    def _overlap(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Hold one audit read until all three independent reads have started."""

        with self._lock:
            self._active += 1
            self.max_active = max(self.max_active, self._active)
        self._barrier.wait(timeout=0.2)
        with self._lock:
            self._active -= 1
        return payload

    def get_source_catalog_children(self, parent_id: str, parent_type: str):
        """Return stable UUID and order identities for five group children."""

        return self._overlap(
            {
                "items": [
                    {"name": "Задача 10", "uuid": "problem-reference"},
                    {"name": "Задача 11", "uuid": "problem-missing-raster"},
                    {"name": "Задача 12", "uuid": "problem-rejected-svg"},
                    {"name": "Задача 13", "uuid": "problem-generated-svg"},
                    {"name": "Задача 14", "uuid": "problem-without-image"},
                ]
            }
        )

    def get_source_catalog_section_images(self, target_id: str, target_type: str):
        """Return compact condition MIME evidence and one generated solution image."""

        return self._overlap(
            {
                "concrete_problem_count": 5,
                "condition": {
                    "problem_count": 5,
                    "problems": [
                        {
                            "source_problem_id": "10",
                            "images": [
                                {
                                    "asset_key": "image_1",
                                    "asset_id": "asset-reference",
                                    "kind": "ordinary_image",
                                    "content_type": "image/png",
                                }
                            ],
                        },
                        {
                            "source_problem_id": "11",
                            "images": [
                                {
                                    "asset_key": "image_1",
                                    "asset_id": "asset-missing-raster",
                                    "kind": "ordinary_image",
                                    "content_type": "image/png",
                                }
                            ],
                        },
                        {
                            "source_problem_id": "12",
                            "images": [
                                {
                                    "asset_key": "image_1",
                                    "asset_id": "asset-rejected-svg",
                                    "kind": "ordinary_image",
                                    "content_type": "image/svg+xml",
                                }
                            ],
                        },
                        {
                            "source_problem_id": "13",
                            "images": [
                                {
                                    "asset_key": "image_1",
                                    "asset_id": "asset-generated-svg",
                                    "kind": "ordinary_image",
                                    "content_type": "image/svg+xml",
                                }
                            ],
                        },
                        {
                            "source_problem_id": "14",
                            "images": [
                                {
                                    "asset_key": "formula_1",
                                    "asset_id": "asset-formula",
                                    "kind": "formula_image",
                                    "content_type": "image/svg+xml",
                                }
                            ],
                        },
                    ],
                },
                "solution": {
                    "problem_count": 1,
                    "problems": [
                        {
                            "source_problem_id": "13",
                            "images": [
                                {
                                    "asset_key": "generated_solution_diagram",
                                    "asset_id": "asset-solution",
                                    "kind": "ordinary_image",
                                    "content_type": "image/svg+xml",
                                }
                            ],
                        }
                    ],
                },
            }
        )

    def get_source_catalog_missing_solution_summary(
        self,
        target_id: str,
        target_type: str,
    ):
        """Return missing-solution identities including rejected and imageless rows."""

        return self._overlap(
            {
                "concrete_problem_count": 5,
                "count": 3,
                "source_problem_ids": ["11", "12", "14"],
            }
        )

    def get_problem_pipeline_state(self, problem_id: str):
        """Reject one intersected candidate while keeping the other two ready."""

        self.state_problem_ids.append(problem_id)
        normalized = "rejected" if problem_id == "problem-rejected-svg" else "ready"
        return {"statuses": {"normalized": normalized}}

    def get_problem_context(self, problem_id: str):
        """Fail if inventory returns to the legacy full-content read path."""

        raise AssertionError(f"unexpected full content read for {problem_id}")

    def get_asset_metadata(self, asset_id: str):
        """Fail because every audit image includes authoritative MIME data."""

        raise AssertionError(f"unexpected metadata lookup for {asset_id}")


def test_inventory_intersects_parallel_audits_before_status_reads() -> None:
    """Build the same rerunnable worklist without per-problem Normalized reads."""

    gateway = AuditInventoryGateway()

    inventory = discover_group_inventory(
        gateway,
        get_group_profile("245008"),
        max_workers=3,
    )

    assert gateway.max_active == 3
    assert set(gateway.state_problem_ids) == {
        "problem-missing-raster",
        "problem-rejected-svg",
        "problem-generated-svg",
    }
    assert [target.source_problem_id for target in inventory.targets] == ["11", "13"]
    assert [target.source_problem_id for target in inventory.png_targets] == ["11"]
    assert [target.source_problem_id for target in inventory.svg_targets] == ["13"]
