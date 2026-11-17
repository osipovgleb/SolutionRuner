"""Resume content stages using the previously frozen manifest."""

from types import SimpleNamespace
from unittest.mock import Mock

from solution_runner.pipelines.core.content_stage import run_content_rule_stage


def test_resume_reads_frozen_manifest_without_preparing_again(tmp_path):
    target = SimpleNamespace(problem_id="parent")
    profile = SimpleNamespace(content_rule_key="rule", condition_asset_id=None)
    read = Mock(return_value={"records": []})
    prepare = Mock()
    services = SimpleNamespace(
        _registered_handler=lambda key: SimpleNamespace(expected_parent_id=None),
        _read_content_rule_manifest=read,
        _content_rule_manifest=prepare,
    )

    result = run_content_rule_stage(
        Mock(),
        (target,),
        target,
        profile,
        Mock(),
        run_dir=tmp_path,
        resume=True,
        apply=False,
        batch_size=1,
        batch_pause_seconds=0,
        max_workers=1,
        services=services,
    )

    assert result == ()
    read.assert_called_once_with(
        tmp_path / "prepared-manifest.json", (target,), profile
    )
    prepare.assert_not_called()


def test_resume_apply_reports_each_completed_record(tmp_path, monkeypatch):
    from solution_runner.pipelines.core import content_stage

    target = SimpleNamespace(problem_id="parent")
    profile = SimpleNamespace(content_rule_key="rule", condition_asset_id=None)
    records = [{"problem_id": "parent", "status": "applied"}]
    manifest = {"records": records}
    apply = Mock(
        side_effect=lambda gateway, data, **kwargs: kwargs["on_batch_complete"](
            records, 1
        )
    )
    services = SimpleNamespace(
        _registered_handler=lambda key: SimpleNamespace(expected_parent_id=None),
        _read_content_rule_manifest=Mock(return_value=manifest),
        apply_frozen_manifest=apply,
    )
    monkeypatch.setattr(
        content_stage,
        "_report_content_result",
        lambda reporter, profile, record, progress: record,
    )
    result = run_content_rule_stage(
        Mock(),
        (target,),
        target,
        profile,
        Mock(),
        run_dir=tmp_path,
        resume=True,
        apply=True,
        batch_size=2,
        batch_pause_seconds=0.5,
        max_workers=3,
        services=services,
    )
    assert result == tuple(records)
    assert apply.call_args.kwargs["checkpoint_path"] == tmp_path / "apply-results.json"
    assert apply.call_args.kwargs["max_workers"] == 3
