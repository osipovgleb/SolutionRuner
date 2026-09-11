from solution_runner.dashboard.previews import load_preview, save_preview
from solution_runner.dashboard.rejections import reject_indexed_problem
from solution_runner.group_inventory_store import (
    GroupInventoryItem,
    GroupInventorySnapshot,
    GroupInventoryStore,
)


def test_reject_problem_uses_specialized_mcp_tool_then_removes_local_task(tmp_path):
    class Gateway:
        def __init__(self):
            self.rejections = []

        def reject_problem_content_pipeline(self, problem_id, reason):
            self.rejections.append((problem_id, reason))
            return {"problem_id": problem_id, "statuses": {"normalized": "rejected"}}

        def get_problem_pipeline_state(self, problem_id):
            return {"problem_id": problem_id, "statuses": {"normalized": "rejected"}}

    inventory = GroupInventoryStore(tmp_path / "dashboard.sqlite3")
    inventory.replace(GroupInventorySnapshot(
        group_key="group", catalog_snapshot_id="catalog", source_group_id="source-group",
        parent_problem_id="parent", parent_source_problem_id="1",
        items=(
            GroupInventoryItem("parent", "1", 0, True, True, True),
            GroupInventoryItem("bad", "2", 1, True, False, True),
        ),
    ))
    preview_dir = tmp_path / "previews"
    save_preview(preview_dir, {
        "group_key": "group",
        "samples": [
            {"problem_id": "parent", "source_problem_id": "1"},
            {"problem_id": "bad", "source_problem_id": "2"},
        ],
    })
    gateway = Gateway()

    result = reject_indexed_problem(
        gateway, inventory, preview_dir, "group", "bad", "Некорректное условие"
    )

    assert result == {"problem_id": "bad", "source_problem_id": "2", "status": "rejected"}
    assert gateway.rejections == [("bad", "Некорректное условие")]
    assert [item["problem_id"] for item in inventory.list_items("group")] == ["parent"]
    assert [item["problem_id"] for item in load_preview(preview_dir, "group")["samples"]] == ["parent"]


def test_reject_problem_requires_confirmed_rejected_readback(tmp_path):
    class Gateway:
        def reject_problem_content_pipeline(self, problem_id, reason):
            return {}

        def get_problem_pipeline_state(self, problem_id):
            return {"statuses": {"normalized": "ready"}}

    inventory = GroupInventoryStore(tmp_path / "dashboard.sqlite3")
    inventory.replace(GroupInventorySnapshot(
        group_key="group", catalog_snapshot_id="catalog", source_group_id="source-group",
        parent_problem_id="parent", parent_source_problem_id="1",
        items=(
            GroupInventoryItem("parent", "1", 0, True, True, True),
            GroupInventoryItem("problem", "2", 1, True, True, True),
        ),
    ))

    try:
        reject_indexed_problem(Gateway(), inventory, tmp_path / "previews", "group", "problem", "Причина")
    except RuntimeError as exc:
        assert "readback" in str(exc)
    else:
        raise AssertionError("a missing rejected readback must keep the task indexed")

    assert [item["problem_id"] for item in inventory.list_items("group")] == ["parent", "problem"]
