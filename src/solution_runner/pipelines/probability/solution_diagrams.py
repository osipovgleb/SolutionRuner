"""Read solution-only figures and prepare exact reuse or verified local SVGs."""

import hashlib
from dataclasses import replace
from html import escape

from solution_runner.pipelines.word_problems.common import rewrite

from .common import UnsupportedCondition, finish, require_content


def read(context):
    content = context.get("normalized_content")
    if not isinstance(content, dict) or not isinstance(content.get("sections"), list):
        raise UnsupportedCondition("normalized sections are required")
    if any(
        s.get("asset_keys") for s in content["sections"] if s.get("key") != "solution"
    ):
        raise UnsupportedCondition("only solution figures are supported by this rule")
    clean = {**context, "normalized_content": {**content, "assets": []}}
    _, condition, answer, solution, text = require_content(clean)
    return content, condition, answer, solution, text


def spec(key, svg):
    return {
        "asset_key": key,
        "svg_text": svg,
        "sha256": hashlib.sha256(svg.encode()).hexdigest(),
    }


def image(content, key, alt, *, source_id=None, svg=None, generated=()):
    changes = []
    if source_id:
        matches = [
            a for a in content.get("assets", []) if a.get("asset_id") == source_id
        ]
        if len(matches) != 1:
            raise UnsupportedCondition(
                "the mathematically compatible source figure is required"
            )
        asset = matches[0]
        key = asset["asset_key"]
        url = asset.get("url") or "/assets/" + source_id
    else:
        matches = [a for a in generated if a.get("asset_key") == key]
        if (
            len(matches) != 1
            or not isinstance(svg, str)
            or matches[0].get("sha256") != hashlib.sha256(svg.encode()).hexdigest()
        ):
            raise UnsupportedCondition(
                "the prepared figure does not match the current mathematical model"
            )
        asset = matches[0]
        source_id = asset["source_asset_id"]
        url = asset["url"]
        if not any(
            a.get("asset_key") == key and a.get("asset_id") == source_id
            for a in content.get("assets", [])
        ):
            changes.append(
                {
                    "transformation_target_id": "asset:" + key,
                    "operation": "add",
                    "value": {
                        "asset_key": key,
                        "asset_id": source_id,
                        "url": url,
                        "kind": "ordinary_image",
                        "alt": alt,
                        "parent_target_id": "section:solution:1",
                        "position": 0,
                    },
                }
            )
    markup = f'<center><img alt="{escape(alt, quote=True)}" data-asset-key="{escape(key, quote=True)}" data-asset-id="{escape(source_id, quote=True)}" src="{escape(url, quote=True)}"/></center>'
    if changes:
        changes[0]["value"]["html"] = markup
    return markup, key, changes


def repair(
    condition, answer_section, solution, answer, html, keys=(), asset_changes=()
):
    plan = finish(condition, answer_section, solution, answer, html)
    changes = list(plan.transformations)
    if not any(
        t["transformation_target_id"].startswith("section:solution") for t in changes
    ) and (solution or {}).get("asset_keys", []) != list(keys):
        changes.append(rewrite(solution, "solution", "Решение", html))
    for change in changes:
        if change["transformation_target_id"].startswith("section:solution"):
            change["value"]["asset_keys"] = list(keys)
    return replace(plan, transformations=tuple(asset_changes) + tuple(changes))
