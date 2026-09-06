"""Registry wiring and parity with the pre-refactor dispatch, without MCP."""
from dataclasses import asdict, replace
from importlib import import_module
import json
from pathlib import Path

import pytest

from solution_runner.pipelines.core.group_profiles import all_group_profiles, build_profile_registry
from solution_runner.pipelines.core.handler_registry import HANDLERS, build_registry, get_handler
from solution_runner.pipelines.core.handlers import HandlerSpec, PlanInput
from solution_runner.pipelines.triangles.right.runtime import _build_content_plan

LEGACY = json.loads((Path(__file__).parent / "fixtures/legacy_handler_dispatch.json").read_text())


@pytest.mark.parametrize("key", sorted(LEGACY))
def test_every_legacy_route_and_argument_is_preserved(key, monkeypatch):
    expected = LEGACY[key]
    handler = get_handler(key)
    handler.validate()
    assert handler.target == expected["target"]
    assert dict(handler.constraints) == expected["constraints"]
    assert handler.requires_parent_condition_asset == expected["requires_parent_condition_asset"]
    assert handler.parent_from_group_listing == key.startswith("general-triangle-")
    assert handler.inspect_current_asset_type == (key in {
        "vector-27707-rectangle-diagonal-length", "vector-27708-rectangle-vector-sum-length",
        "vector-27718-rhombus-diagonal-difference",
    })
    assert handler.strict_frozen_input == (key == "general-triangle-27591-area-sas-30")
    module, name = handler.target.split(":")
    sentinel = object()
    context = {"condition": "sentinel, never parsed"}

    def capture(actual, **kwargs):
        assert actual is context
        assert kwargs == expected["kwargs"]
        return sentinel

    monkeypatch.setattr(import_module(module), name, capture)
    assert _build_content_plan(
        context, content_rule_key=key, parent_asset_id="@parent_asset_id",
        parent_solution_html="@parent_solution_html",
        parent_solution_assets="@parent_solution_assets",
        current_asset_content_type="@current_asset_content_type",
    ) is sentinel


def test_all_content_profiles_resolve_to_registered_handlers():
    for profile in all_group_profiles().values():
        if profile.workflow_kind == "content_rule":
            get_handler(profile.content_rule_key).validate()


def test_unknown_rule_does_not_fall_back_to_general_triangle():
    with pytest.raises(KeyError, match="unsupported content rule"):
        get_handler("general-triangle-unknown")


def test_duplicate_registry_key_is_rejected():
    spec = next(iter(HANDLERS.values()))
    with pytest.raises(ValueError, match="duplicate handler"):
        build_registry([spec, spec])


def test_registry_is_immutable():
    with pytest.raises(TypeError):
        HANDLERS["new"] = next(iter(HANDLERS.values()))


def test_bad_adapter_argument_is_rejected():
    with pytest.raises(ValueError, match="unknown PlanInput"):
        HandlerSpec("bad", "module:function", inputs=(("image", "typo"),))


def test_new_binding_needs_no_dispatch_branch():
    existing = get_handler("irrational-26660-square-root-rational-affine")
    alias = replace(existing, key="test-another-group-same-math")
    registry = build_registry([existing, alias])
    assert registry[alias.key].target == existing.target


def test_every_profile_survives_domain_split():
    expected = json.loads((Path(__file__).parent / "fixtures/legacy_group_profiles.json").read_text())
    actual = json.loads(json.dumps({k: asdict(v) for k, v in all_group_profiles().items()}))
    # Preserve every migrated profile; later registrations are validated by
    # test_all_content_profiles_resolve_to_registered_handlers independently.
    assert {key: actual[key] for key in expected} == expected


def test_new_group_selects_existing_handler_without_core_changes():
    prototype = all_group_profiles()["26661"]
    new_group = replace(prototype, group_key="test-new-group", source_group_id="test-id")
    registry = build_profile_registry([prototype, new_group])
    assert get_handler(registry[new_group.group_key].content_rule_key) is get_handler(prototype.content_rule_key)


def test_unknown_profile_handler_is_rejected_at_registration():
    profile = replace(all_group_profiles()["26661"], content_rule_key="typo")
    with pytest.raises(KeyError, match="unsupported content rule"):
        build_profile_registry([profile])


def test_duplicate_group_is_rejected_at_registration():
    profile = all_group_profiles()["26661"]
    with pytest.raises(ValueError, match="duplicate group"):
        build_profile_registry([profile, profile])


def test_old_runtime_import_is_only_a_compatibility_alias():
    from solution_runner.pipelines.core import content_runtime
    from solution_runner.pipelines.triangles.right import runtime
    assert runtime is content_runtime


def test_core_runtime_has_no_domain_dispatch_or_group_ids():
    import ast
    import inspect
    from solution_runner.pipelines.core import content_runtime
    tree = ast.parse(inspect.getsource(content_runtime))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            assert not (node.module or "").startswith((
                "solution_runner.pipelines.equations", "solution_runner.pipelines.vectors",
                "solution_runner.pipelines.triangles", "solution_runner.pipelines.quadrilaterals",
            ))
        if isinstance(node, ast.Compare):
            assert not any(isinstance(value, ast.Constant) and isinstance(value.value, str)
                           and value.value in HANDLERS for value in node.comparators)
