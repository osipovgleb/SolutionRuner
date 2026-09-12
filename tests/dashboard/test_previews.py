from types import SimpleNamespace

import json
import pytest

from solution_runner.dashboard.previews import (
    ProblemPreviewUnavailable,
    fetch_problem_preview,
    fetch_preview,
    latest_dry_run_manifest,
    load_preview,
    save_preview,
)


class FakeGateway:
    def get_problem_context(self, problem_id):
        assert problem_id == "child"
        return {"normalized_content": {
            "sections": [
                {"key": "condition", "transformation_target_id": "section:condition:1", "html": f'<p onclick="bad()">Условие {problem_id}<img data-asset-key="image_1"><script>bad()</script></p>'},
                {"key": "answer", "transformation_target_id": "section:answer:1", "html": "<p>42</p>"},
                {"key": "solution", "transformation_target_id": "section:solution:1", "html": '<span data-inline-latex="x=42"></span>'},
            ],
            "assets": [{"asset_key": "image_1", "url": "/assets/picture"}],
        }}

def test_preview_compares_normalized_input_with_local_dry_run_result(tmp_path):
    manifest = {"group_key": "7", "records": [{
        "problem_id": "child",
        "source_problem_id": "101",
        "transformations": [{
            "operation": "rewrite",
            "transformation_target_id": "section:solution:1",
            "value": {"html": '<span data-inline-latex="x=99"></span>'},
        }],
    }]}
    preview = fetch_preview(
        FakeGateway(),
        SimpleNamespace(group_key="7", source_group_id="group-uuid"),
        manifest,
    )

    sample = preview["samples"][0]
    assert sample["source_problem_id"] == "101"
    assert 'data-inline-latex="x=42"' in sample["before"]["solution_html"]
    assert 'data-inline-latex="x=99"' in sample["after"]["solution_html"]
    assert "onclick" not in sample["before"]["condition_html"]
    assert "<script" not in sample["before"]["condition_html"]
    assert 'src="https://lessons-helper.ru/assets/picture"' in sample["before"]["condition_html"]

    save_preview(tmp_path, preview)
    assert load_preview(tmp_path, "7") == preview


def test_preview_keeps_a_valid_no_change_dry_run_sample():
    manifest = {"group_key": "7", "records": [{
        "problem_id": "child",
        "source_problem_id": "101",
        "transformations": [],
    }]}

    sample = fetch_preview(
        FakeGateway(),
        SimpleNamespace(group_key="7", source_group_id="group-uuid"),
        manifest,
    )["samples"][0]

    assert sample["before"] == sample["after"]


def test_problem_preview_falls_back_to_normalized_content_without_a_dry_run(tmp_path):
    class Gateway:
        def get_problem_pipeline_state(self, problem_id):
            assert problem_id == "problem"
            return {"statuses": {"normalized": "ready"}}

        def get_problem_context(self, problem_id):
            assert problem_id == "problem"
            return {"normalized_content": {
                "sections": [{"key": "condition", "html": "<p>Условие</p>"}],
                "assets": [],
            }}

    preview = fetch_problem_preview(
        Gateway(), tmp_path, "group", "problem", "42"
    )

    assert preview["samples"][0]["before"]["condition_html"] == "<p>Условие</p>"
    assert preview["samples"][0]["after"] is None


def test_problem_preview_opens_indexed_content_marked_rejected_for_review(tmp_path):
    class Gateway:
        def get_problem_context(self, problem_id):
            return {"normalized_content": {
                "sections": [{"key": "condition", "html": "<p>Условие для проверки</p>"}],
                "assets": [],
            }}

    preview = fetch_problem_preview(Gateway(), tmp_path, "group", "problem", "42")

    assert preview["samples"][0]["before"]["condition_html"] == "<p>Условие для проверки</p>"


def test_geometry_dry_run_reads_planned_transformations_from_solution_results(tmp_path):
    run_dir = tmp_path / "grid-polygon/runs/20260910T120000Z-group-7"
    run_dir.mkdir(parents=True)
    (run_dir / "prepared-manifest.json").write_text(json.dumps({
        "schema_version": 1,
        "scope": {"group_key": "7"},
        "records": [{"problem_id": "child", "source_problem_id": "101"}],
    }))
    (run_dir / "solution-results.json").write_text(json.dumps([{
        "problem_id": "child",
        "source_problem_id": "101",
        "status": "planned",
        "transformations": [{
            "operation": "rewrite",
            "transformation_target_id": "section:answer:1",
            "value": {"html": "<p>99</p>"},
        }],
    }]))

    manifest = latest_dry_run_manifest(tmp_path, "7")

    assert manifest["records"][0]["transformations"][0]["value"]["html"] == "<p>99</p>"


def test_empty_solution_result_does_not_erase_prepared_transformations(tmp_path):
    run_dir = tmp_path / "grid-polygon/runs/20260910T120000Z-group-7"
    run_dir.mkdir(parents=True)
    prepared = [{
        "operation": "add",
        "transformation_target_id": "section:solution",
        "value": {"html": "<p>Решение</p>"},
    }]
    (run_dir / "prepared-manifest.json").write_text(json.dumps({
        "group_key": "7",
        "records": [{
            "problem_id": "child",
            "source_problem_id": "101",
            "transformations": prepared,
        }],
    }))
    (run_dir / "solution-results.json").write_text(json.dumps([{
        "problem_id": "child",
        "status": "planned",
        "transformations": [],
    }]))

    manifest = latest_dry_run_manifest(tmp_path, "7")

    assert manifest["records"][0]["transformations"] == prepared


def test_preview_remains_available_after_its_dry_run_was_applied(tmp_path):
    run_dir = tmp_path / "equations/runs/20260910T120000Z-group-7"
    run_dir.mkdir(parents=True)
    (run_dir / "prepared-manifest.json").write_text(json.dumps({
        "group_key": "7",
        "records": [{
            "problem_id": "child", "source_problem_id": "101",
            "transformations": [],
        }],
    }))
    (run_dir / "apply-results.json").write_text("[]")

    assert latest_dry_run_manifest(tmp_path, "7")["records"][0]["problem_id"] == "child"


def test_preview_materializes_new_sections_from_a_geometry_plan():
    class EmptyGateway:
        def get_problem_context(self, problem_id):
            return {"normalized_content": {"sections": [], "assets": []}}

    manifest = {"group_key": "7", "records": [{
        "problem_id": "child",
        "source_problem_id": "101",
        "transformations": [{
            "operation": "add",
            "transformation_target_id": "section:solution",
            "value": {"title": "Решение", "html": "<p>Подробное решение</p>"},
        }],
    }]}

    sample = fetch_preview(
        EmptyGateway(),
        SimpleNamespace(group_key="7", source_group_id="group-uuid"),
        manifest,
    )["samples"][0]

    assert sample["before"]["solution_html"] == ""
    assert sample["after"]["solution_html"] == "<p>Подробное решение</p>"


def test_preview_materializes_attached_assets_and_keeps_referenced_section_assets():
    class Gateway:
        def get_problem_context(self, problem_id):
            return {"normalized_content": {
                "sections": [
                    {
                        "key": "condition",
                        "transformation_target_id": "section:condition:1",
                        "html": "<p>Условие</p>",
                        "asset_keys": [],
                    },
                    {
                        "key": "solution",
                        "transformation_target_id": "section:solution:1",
                        "html": '<p><img data-asset-key="old" src="/assets/old"/></p><p>Старое решение</p>',
                        "asset_keys": ["old"],
                    },
                ],
                "assets": [{"asset_key": "old", "url": "/assets/old"}],
            }}

    manifest = {"group_key": "7", "records": [{
        "problem_id": "child",
        "source_problem_id": "101",
        "transformations": [
            {
                "operation": "rewrite",
                "transformation_target_id": "section:solution:1",
                "value": {"html": "<p>Новое решение</p>", "asset_keys": ["old"]},
            },
            {
                "operation": "add",
                "transformation_target_id": "asset:new",
                "value": {
                    "asset_key": "new",
                    "url": "/assets/new",
                    "parent_target_id": "section:condition:1",
                    "position": 0,
                    "html": '<center><img data-asset-key="new" src="/assets/new"/></center>',
                },
            },
        ],
    }]}

    after = fetch_preview(
        Gateway(),
        SimpleNamespace(group_key="7", source_group_id="group-uuid"),
        manifest,
    )["samples"][0]["after"]

    assert 'src="https://lessons-helper.ru/assets/new"' in after["condition_html"]
    assert 'src="https://lessons-helper.ru/assets/old"' in after["solution_html"]
