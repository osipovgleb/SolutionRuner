from types import SimpleNamespace

from solution_runner.dashboard.initialization import GroupInitializer
from solution_runner.group_inventory_store import GroupInventoryStore


class FakeGateway:
    def __init__(self):
        self.closed = False
        self.metadata_reads = []

    def get_source_catalog_children(self, parent_id, parent_type):
        assert (parent_id, parent_type) == ("source-group", "group")
        return {
            "items": [
                {"uuid": "parent", "name": "Задача 10"},
                {"uuid": "child", "name": "Задача 11"},
            ]
        }

    def find_source_catalog_path(self, catalog_id, query, target_type):
        assert (catalog_id, query, target_type) == ("4073fc7b-2056-4697-b18b-38741c94d0f4", "123", "group")
        return {"matches": [{
            "category": {"uuid": "category"},
            "theme": {"uuid": "theme"},
            "group": {"uuid": "source-group", "name": "Группа 123"},
        }]}

    def get_problem_context(self, problem_id):
        sections = [
            {"key": "condition", "html": "not persisted", "asset_keys": ["image_1"]},
            {"key": "answer", "html": "42"},
        ]
        if problem_id == "parent":
            sections.append({"key": "solution", "html": "not persisted", "asset_keys": ["diagram"]})
        return {
            "normalized_content": {
                "sections": sections,
                "assets": [
                    {"asset_id": "shared", "asset_key": "image_1"},
                    *([{"asset_id": "solution-svg", "asset_key": "diagram"}] if problem_id == "parent" else []),
                ],
            }
        }

    def get_asset_metadata(self, asset_id):
        self.metadata_reads.append(asset_id)
        return {
            "content_type": "image/svg+xml" if asset_id == "solution-svg" else "image/png"
        }

    def close(self):
        self.closed = True


class BatchGateway(FakeGateway):
    def __init__(self):
        super().__init__()
        self.batch_reads = []

    def get_problem_batch(self, problem_ids):
        self.batch_reads.append(tuple(problem_ids))
        return {
            "items": [
                {
                    "problem_id": problem_id,
                    "source_problem_id": "10" if problem_id == "parent" else "11",
                    **self.get_problem_context(problem_id),
                }
                for problem_id in problem_ids
            ]
        }

    def get_source_catalog_section_images(self, parent_id, parent_type):
        assert (parent_id, parent_type) == ("source-group", "group")
        return {
            "condition": {"problems": [{
                "source_problem_id": "10",
                "images": [{
                    "asset_id": "shared", "asset_key": "image_1",
                    "content_type": "image/png", "kind": "ordinary_image",
                }],
            }, {
                "source_problem_id": "11",
                "images": [{
                    "asset_id": "shared", "asset_key": "image_1",
                    "content_type": "image/png", "kind": "ordinary_image",
                }],
            }]},
            "solution": {"problems": [{
                "source_problem_id": "10",
                "images": [{
                    "asset_id": "solution-svg", "asset_key": "diagram",
                    "content_type": "image/svg+xml", "kind": "ordinary_image",
                }],
            }]},
        }


class BatchGatewayWithUnavailable(BatchGateway):
    def get_problem_batch(self, problem_ids):
        if "child" in problem_ids:
            raise RuntimeError("Normalized content is unavailable")
        return super().get_problem_batch(problem_ids)

    def get_problem_pipeline_state(self, problem_id):
        return {
            "problem_id": problem_id,
            "statuses": {"normalized": "rejected" if problem_id == "child" else "ready"},
        }


def _profile():
    return SimpleNamespace(
        group_key="123",
        catalog_snapshot_id="catalog",
        source_group_id="source-group",
    )


def test_initializer_stores_identity_sections_and_asset_types_without_content(tmp_path):
    gateway = FakeGateway()
    store = GroupInventoryStore(tmp_path / "dashboard.sqlite3")
    initializer = GroupInitializer(
        profiles={"123": _profile()},
        inventory_store=store,
        gateway_factory=lambda: gateway,
    )

    state = initializer.run_now("123")

    assert state["status"] == "ready"
    snapshot = store.get("123")
    assert snapshot.parent_problem_id == "parent"
    assert snapshot.parent_source_problem_id == "10"
    assert [(item.problem_id, item.source_problem_id, item.position) for item in snapshot.items] == [
        ("parent", "10", 0),
        ("child", "11", 1),
    ]
    assert snapshot.items[0].has_solution is True
    assert snapshot.items[1].has_solution is False
    assert {(asset.asset_key, asset.section_key, asset.content_type) for asset in snapshot.assets} == {
        ("image_1", "condition", "image/png"),
        ("diagram", "solution", "image/svg+xml"),
    }
    assert sorted(gateway.metadata_reads) == ["shared", "solution-svg"]
    assert "not persisted" not in repr(snapshot)
    assert gateway.closed is True


def test_initializer_uses_batched_problem_reads_and_group_image_metadata(tmp_path):
    gateway = BatchGateway()
    store = GroupInventoryStore(tmp_path / "dashboard.sqlite3")
    initializer = GroupInitializer(
        profiles={"123": _profile()},
        inventory_store=store,
        gateway_factory=lambda: gateway,
    )

    state = initializer.run_now("123")

    assert state["status"] == "ready"
    assert gateway.batch_reads == [("parent", "child")]
    assert gateway.metadata_reads == []
    assert {asset.content_type for asset in store.get("123").assets} == {
        "image/png", "image/svg+xml",
    }


def test_rejected_problem_is_skipped_without_blocking_its_group(tmp_path):
    gateway = BatchGatewayWithUnavailable()
    store = GroupInventoryStore(tmp_path / "dashboard.sqlite3")
    initializer = GroupInitializer(
        profiles={"123": _profile()},
        inventory_store=store,
        gateway_factory=lambda: gateway,
    )

    state = initializer.run_now("123")

    assert state["status"] == "ready"
    assert state["unavailable"] == 0
    assert state["rejected"] == 1
    (parent,) = store.get("123").items
    assert parent.content_status == "available"


def test_failed_initializer_keeps_previous_snapshot_until_explicit_retry(tmp_path):
    store = GroupInventoryStore(tmp_path / "dashboard.sqlite3")
    good = GroupInitializer(
        profiles={"123": _profile()},
        inventory_store=store,
        gateway_factory=FakeGateway,
    )
    good.run_now("123")

    broken = GroupInitializer(
        profiles={"123": _profile()},
        inventory_store=store,
        gateway_factory=lambda: SimpleNamespace(
            get_source_catalog_children=lambda *_: (_ for _ in ()).throw(RuntimeError("offline")),
            close=lambda: None,
        ),
    )
    state = broken.run_now("123")

    assert state["status"] == "failed"
    assert store.get("123").items
    assert broken.get("123")["status"] == "failed"


def test_initializer_resolves_an_unregistered_group_from_dashboard_coordinates(tmp_path):
    store = GroupInventoryStore(tmp_path / "dashboard.sqlite3")
    resolved = []
    initializer = GroupInitializer(
        profiles={},
        group_source_lookup=lambda key: {"source_id": "4073fc7b-2056-4697-b18b-38741c94d0f4"} if key == "123" else None,
        inventory_store=store,
        gateway_factory=FakeGateway,
        on_resolved=lambda group_key, navigation: resolved.append((group_key, navigation)),
    )

    state = initializer.run_now("123")

    assert state["status"] == "ready"
    assert store.get("123").source_group_id == "source-group"
    assert resolved == [("123", {
        "source_site_id": "7bed2492-5b8b-4c88-9be8-7d47916cd7c6",
        "snapshot_id": "4073fc7b-2056-4697-b18b-38741c94d0f4",
        "category_id": "category",
        "theme_id": "theme",
        "group_id": "source-group",
    })]
