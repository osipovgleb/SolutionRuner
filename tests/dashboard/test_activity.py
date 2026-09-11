import json

from solution_runner.dashboard.activity import load_group_activity
from solution_runner.group_inventory_store import (
    GroupInventoryItem,
    GroupInventorySnapshot,
    GroupInventoryStore,
    GroupItemStageResult,
)


def _write(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_activity_lists_saved_runs_and_unresolved_task_problems(tmp_path):
    run = tmp_path / "var/runs/20260907T212750Z-group-ege-base-77391"
    _write(run / "summary.json", {
        "group_key": "ege-base-77391", "status": "completed_with_errors",
        "targets": 253, "failed_stage_results": 1, "apply": True,
    })
    inventory = GroupInventoryStore(tmp_path / "dashboard.sqlite3")
    inventory.replace(GroupInventorySnapshot(
        group_key="ege-base-77391", catalog_snapshot_id="catalog",
        source_group_id="source-group", parent_problem_id="problem",
        parent_source_problem_id="87249",
        items=(GroupInventoryItem("problem", "87249", 0, True, True, True),),
    ))
    inventory.update_item_stage(GroupItemStageResult(
        group_key="ege-base-77391", problem_id="problem",
        apply_status="applied", helpers_status="failed", error="write fence is busy",
    ))

    activity = load_group_activity(tmp_path / "var", "ege-base-77391", inventory)

    assert activity["latest"]["kind"] == "apply"
    assert activity["latest"]["targets"] == 253
    assert activity["runs"][0]["failed"] == 1
    assert activity["problems"] == [{
        "problem_id": "problem", "source_problem_id": "87249",
        "apply_status": "applied", "helpers_status": "failed",
        "error": "write fence is busy",
    }]
