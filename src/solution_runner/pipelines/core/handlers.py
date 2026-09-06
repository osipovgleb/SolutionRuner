"""Domain-neutral input and explicit adapters for existing pure planners."""
from dataclasses import dataclass, fields
from importlib import import_module
from inspect import signature
from typing import Any, Protocol


class RepairPlan(Protocol):
    answer: str
    transformations: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class PlanInput:
    context: dict[str, Any]
    parent_asset_id: str | None = None
    parent_solution_assets: tuple[dict[str, str], ...] = ()
    parent_solution_html: str = ""
    current_asset_content_type: str | None = None


@dataclass(frozen=True)
class HandlerSpec:
    """One explicit rule, its planner adapter, and its immutable requirements.

    Import paths are trusted repository declarations, never user/MCP input.
    inputs maps legacy keyword names to PlanInput fields; options holds fixed
    per-rule arguments. All callers use PlanInput regardless of legacy signature.
    """

    key: str
    target: str
    inputs: tuple[tuple[str, str], ...] = ()
    options: tuple[tuple[str, Any], ...] = ()
    constraints: tuple[tuple[str, str], ...] = ()
    requires_parent_condition_asset: bool = True
    inspect_current_asset_type: bool = False
    parent_from_group_listing: bool = False
    expected_parent_id: str | None = None
    strict_frozen_input: bool = False
    requires_frozen_manifest: bool = False
    manifest_validator: str | None = None

    def __post_init__(self):
        if not self.key or ':' not in self.target:
            raise ValueError("handler needs an explicit key and module:function")
        allowed = {f.name for f in fields(PlanInput)} - {"context"}
        if any(source not in allowed for _, source in self.inputs):
            raise ValueError(f"unknown PlanInput field for {self.key}")
        names = [name for name, _ in self.inputs + self.options]
        if len(set(names)) != len(names):
            raise ValueError(f"duplicate planner argument for {self.key}")

    def resolve(self):
        module, name = self.target.split(':', 1)
        planner = getattr(import_module(module), name)
        if not callable(planner):
            raise TypeError(f"planner is not callable: {self.target}")
        return planner

    def arguments(self, value: PlanInput) -> dict[str, Any]:
        return {**{name: getattr(value, source) for name, source in self.inputs},
                **dict(self.options)}

    def validate(self) -> None:
        """Check declaration wiring without reading a problem or invoking math."""
        signature(self.resolve()).bind({}, **self.arguments(PlanInput({})))
        if self.manifest_validator:
            module, name = self.manifest_validator.split(":", 1)
            signature(getattr(import_module(module), name)).bind(None, {})

    def validate_manifest(self, gateway, manifest) -> None:
        if self.manifest_validator:
            module, name = self.manifest_validator.split(":", 1)
            getattr(import_module(module), name)(gateway, manifest)

    def plan(self, value: PlanInput) -> RepairPlan:
        return self.resolve()(value.context, **self.arguments(value))
