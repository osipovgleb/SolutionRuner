"""Prepare graph plans and replay their transformations only in copied local data."""

from copy import deepcopy

from solution_runner.pipelines.calculus import graph_input
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput


def plan(case, context, *, downloaded=None, generated=None):
    handler = get_handler(get_group_profile(case["group"]).content_rule_key)
    content = case["context"]["normalized_content"]
    condition = next(s for s in content["sections"] if s["key"] == "condition")
    asset = next(
        a for a in content["assets"] if a["asset_key"] in condition["asset_keys"]
    )
    entry = graph_input.EVIDENCE[asset["asset_id"]]
    source = (
        graph_input.ASSETS
        / entry.get("filename", asset["asset_id"] + entry.get("extension", ".svg"))
    ).read_bytes()
    if generated is None:
        generated = tuple(
            {
                **spec,
                "source_asset_id": "local-prepared-triangle",
                "url": "/assets/local-prepared-triangle",
            }
            for spec in handler.diagram_specs(context)
        )
    return handler.plan(
        PlanInput(
            context,
            condition_asset_bytes=source if downloaded is None else downloaded,
            generated_solution_assets=generated,
        )
    )


def _apply_local(context, transformations):
    content = context["normalized_content"]
    for t in transformations:
        if t["transformation_target_id"].startswith("asset:"):
            if t["operation"] == "remove":
                key = t["transformation_target_id"].removeprefix("asset:")
                content["assets"] = [
                    a for a in content["assets"] if a["asset_key"] != key
                ]
            else:
                content["assets"].append(deepcopy(t["value"]))
            continue
        section = next(
            (
                s
                for s in content["sections"]
                if s["transformation_target_id"] == t["transformation_target_id"]
            ),
            None,
        )
        if section is None:
            key = t["transformation_target_id"].split(":")[1]
            section = {
                "key": key,
                "section_id": key + ":1",
                "transformation_target_id": t["transformation_target_id"],
            }
            content["sections"].append(section)
        section.update(t["value"])
