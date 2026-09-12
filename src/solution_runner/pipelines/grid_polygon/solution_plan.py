"""Build and verify reusable solution/answer transformation plans."""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
import re
from typing import Any, Sequence

from bs4 import BeautifulSoup

from .mcp_runtime import McpGateway
from ..core.models import GeometryAnalysis, GroupProfile, PreparedFigure
from .strategies.protocol import SolutionStrategy


SOLUTION_ASSET_KEY = "generated_solution_diagram"
SOLUTION_ASSET_TARGET = f"asset:{SOLUTION_ASSET_KEY}"
PICK_ASSET_KEY = "generated_pick_diagram"
RECTANGLE_ASSET_KEY = "generated_rectangle_diagram"
PIPELINE_ASSET_KEYS = (
    SOLUTION_ASSET_KEY,
    RECTANGLE_ASSET_KEY,
    PICK_ASSET_KEY,
)


class SolutionRuntimeError(RuntimeError):
    """Report one target-local solution or answer failure."""


class AnswerVerificationError(SolutionRuntimeError):
    """Report an answer that did not match authoritative readback."""


@dataclass(frozen=True)
class SolutionPlan:
    """Carry one exact transformation batch and its required readback."""

    transformations: tuple[dict[str, Any], ...]
    solution_html: str
    answer_html: str
    answer_audit: str
    asset_target_ids: tuple[tuple[str, str], ...]


def normalized_content(context: dict[str, Any]) -> dict[str, Any]:
    """Validate and return one schema-v3 normalized content object."""

    content = context.get("normalized_content")
    if (
        not isinstance(content, dict)
        or content.get("format") != "teacherhelper-normalized"
        or content.get("schema_version") != 3
    ):
        raise SolutionRuntimeError("schema-v3 Normalized content is required")
    return content


def _section(content: dict[str, Any], key: str) -> dict[str, Any] | None:
    """Return one unique normalized section by canonical key."""

    matches = [
        item
        for item in content.get("sections", [])
        if isinstance(item, dict) and item.get("key") == key
    ]
    if len(matches) > 1:
        raise SolutionRuntimeError(f"multiple {key!r} sections are present")
    return matches[0] if matches else None


def _strip_generated_diagrams(value: str) -> str:
    """Remove only diagram blocks produced by this pipeline."""

    return re.sub(
        r'<center>\s*<img\b(?=[^>]*data-asset-key=["\'](?:'
        + "|".join(map(re.escape, PIPELINE_ASSET_KEYS))
        + r')["\'])[^>]*>\s*</center>',
        "",
        value,
        flags=re.IGNORECASE,
    )


def _section_transformation(
    key: str,
    title: str,
    body: str,
    *,
    section: dict[str, Any] | None,
    asset_keys: Sequence[str] = (),
) -> dict[str, Any]:
    """Build one exact section add/rewrite transformation."""

    target_id = f"section:{key}"
    if section is not None:
        exact_target_id = str(section.get("transformation_target_id") or "")
        section_id = str(section.get("section_id") or "")
        if exact_target_id:
            target_id = exact_target_id
        elif section_id:
            target_id = f"section:{section_id}"
    return {
        "transformation_target_id": target_id,
        "operation": "rewrite" if section is not None else "add",
        "value": {
            "title": title,
            "html": body,
            "asset_keys": list(asset_keys),
        },
    }


def _centered_asset_html(
    *,
    asset_key: str,
    source_asset_id: str,
    asset_url: str,
    alt_text: str,
) -> str:
    """Build one centered solution image placed before explanation prose."""

    target = f"asset:{asset_key}"
    return (
        f'<center><img src="{escape(asset_url, quote=True)}" '
        f'alt="{escape(alt_text, quote=True)}" '
        f'data-asset-id="{escape(source_asset_id, quote=True)}" '
        f'data-asset-key="{escape(asset_key, quote=True)}" '
        f'data-transformation-target-id="{escape(target, quote=True)}"></center>'
    )


def _place_solution_diagrams(
    solution_html: str,
    diagrams: Sequence[tuple[int, str]],
) -> str:
    """Place each generated diagram inside its explicit solution variant."""

    variants = list(re.finditer(
        r'<section\b(?=[^>]*\bdata-content-kind\s*=\s*["\']solution["\'])[^>]*>',
        solution_html,
        flags=re.IGNORECASE,
    ))
    if not diagrams:
        return solution_html
    if not variants:
        if len(diagrams) == 1 and diagrams[0][0] == 0:
            return diagrams[0][1] + solution_html
        raise SolutionRuntimeError("solution diagram variant is missing")
    result = solution_html
    for variant_index, centered in sorted(diagrams, reverse=True):
        if variant_index < 0 or variant_index >= len(variants):
            raise SolutionRuntimeError("solution diagram variant is missing")
        insertion = variants[variant_index].end()
        result = result[:insertion] + centered + result[insertion:]
    return result


def _references_asset_key(solution_html: str, asset_key: str) -> bool:
    """Return whether final solution HTML still references one prior asset key."""

    return bool(
        re.search(
            r'\bdata-asset-key\s*=\s*["\']'
            + re.escape(asset_key)
            + r'["\']',
            solution_html,
            flags=re.IGNORECASE,
        )
    )


def _solution_transformations(
    content: dict[str, Any],
    prepared: PreparedFigure,
    analysis: GeometryAnalysis,
    profile: GroupProfile,
    strategy: SolutionStrategy,
    uploaded: Sequence[dict[str, Any]],
) -> tuple[list[dict[str, Any]], str, tuple[tuple[str, str], ...]]:
    """Build the solution section and optional generated-asset transformation."""

    solution = _section(content, "solution")
    existing = (
        _strip_generated_diagrams(str(solution.get("html") or ""))
        if solution is not None
        else ""
    )
    preserve = profile.existing_solution_policy == "preserve" and bool(existing.strip())
    solution_text = (
        existing if preserve else strategy.build_solution_html(analysis, profile)
    )
    prior_keys = tuple(
        str(value)
        for value in (solution.get("asset_keys", []) if solution is not None else [])
        if str(value)
    )
    existing_keys = tuple(
        asset_key
        for asset_key in prior_keys
        if asset_key not in PIPELINE_ASSET_KEYS
        and _references_asset_key(solution_text, asset_key)
    )
    stale_keys = tuple(
        asset_key
        for asset_key in prior_keys
        if asset_key not in PIPELINE_ASSET_KEYS and asset_key not in existing_keys
    )
    centered_diagrams: list[tuple[int, str]] = []
    diagram_items: list[dict[str, Any]] = []
    asset_target_ids: list[tuple[str, str]] = []
    seen_keys: set[str] = set()
    asset_key_order: list[str] = []
    for item in uploaded:
        asset_key = str(item.get("asset_key") or "")
        source_asset_id = str(item.get("source_asset_id") or "")
        asset_url = str(item.get("url") or "")
        alt_text = str(item.get("alt_text") or "")
        try:
            variant_index = int(item.get("solution_variant_index") or 0)
        except (TypeError, ValueError) as exc:
            raise SolutionRuntimeError("solution diagram variant is invalid") from exc
        if not asset_key or asset_key in seen_keys or not source_asset_id or not asset_url:
            raise SolutionRuntimeError("uploaded solution asset identity is incomplete")
        seen_keys.add(asset_key)
        asset_key_order.append(asset_key)
        centered = _centered_asset_html(
            asset_key=asset_key,
            source_asset_id=source_asset_id,
            asset_url=asset_url,
            alt_text=alt_text,
        )
        centered_diagrams.append((variant_index, centered))
        diagram_items.append({**item, "html": centered})
        asset_target_ids.append((f"asset:{asset_key}", source_asset_id))
    solution_html = _place_solution_diagrams(solution_text, centered_diagrams)
    asset_keys = (*asset_key_order, *existing_keys)
    section_transformation = _section_transformation(
        "solution",
        "Решение",
        solution_html,
        section=solution,
        asset_keys=asset_keys,
    )
    removals: list[dict[str, Any]] = [
        {
            "transformation_target_id": f"asset:{asset_key}",
            "operation": "remove",
        }
        for asset_key in stale_keys
    ]
    removals.extend(
        {
            "transformation_target_id": f"asset:{asset_key}",
            "operation": "remove",
        }
        for asset_key in PIPELINE_ASSET_KEYS
        if asset_key not in seen_keys
        and any(
            isinstance(asset, dict) and asset.get("asset_key") == asset_key
            for asset in content.get("assets", [])
        )
    )
    additions = [_asset_transformation(content, item) for item in diagram_items]
    transformations = [*additions, section_transformation, *removals]
    return transformations, solution_html, tuple(asset_target_ids)


def _asset_transformation(
    content: dict[str, Any],
    uploaded: dict[str, Any],
) -> dict[str, Any]:
    """Upsert the pipeline-owned asset through its original add operation."""

    asset_key = str(uploaded.get("asset_key") or "")
    source_asset_id = str(uploaded.get("source_asset_id") or "")
    if not asset_key or not source_asset_id:
        raise SolutionRuntimeError("solution asset transformation is incomplete")
    current_assets = [
        item
        for item in content.get("assets", [])
        if isinstance(item, dict) and item.get("asset_key") == asset_key
    ]
    if len(current_assets) > 1:
        raise SolutionRuntimeError("multiple generated solution assets are present")
    return {
        "transformation_target_id": f"asset:{asset_key}",
        "operation": "add",
        "value": {
            "parent_target_id": "section:solution",
            "position": int(uploaded.get("solution_variant_index") or 0),
            "asset_key": asset_key,
            "asset_id": source_asset_id,
            "url": uploaded["url"],
            "kind": "ordinary_image",
            "alt": str(uploaded.get("alt_text") or ""),
            "html": str(uploaded.get("html") or ""),
        },
    }


def _answer_transformation(
    content: dict[str, Any],
    analysis: GeometryAnalysis,
    strategy: SolutionStrategy,
) -> tuple[dict[str, Any], str, str]:
    """Build the verified answer operation and pre-write audit label."""

    answer = _section(content, "answer")
    answer_html = strategy.build_answer_html(analysis)
    old_answer = str(answer.get("html") or "") if answer is not None else ""
    if not old_answer.strip():
        audit = "answer_empty_before_write"
    elif old_answer == answer_html:
        audit = "answer_verified_before_write"
    else:
        audit = "answer_mismatch_before_write"
    return (
        _section_transformation(
            "answer",
            "Ответ",
            answer_html,
            section=answer,
        ),
        answer_html,
        audit,
    )


def build_solution_plan(
    content: dict[str, Any],
    prepared: PreparedFigure,
    analysis: GeometryAnalysis,
    profile: GroupProfile,
    strategy: SolutionStrategy,
    uploaded: Sequence[dict[str, Any]],
) -> SolutionPlan:
    """Build one exact solution, optional asset, and answer plan."""

    transformations, solution_html, asset_target_ids = _solution_transformations(
        content,
        prepared,
        analysis,
        profile,
        strategy,
        uploaded,
    )
    answer_transformation, answer_html, audit = _answer_transformation(
        content,
        analysis,
        strategy,
    )
    transformations.append(answer_transformation)
    return SolutionPlan(
        transformations=tuple(transformations),
        solution_html=solution_html,
        answer_html=answer_html,
        answer_audit=audit,
        asset_target_ids=asset_target_ids,
    )


def verify_solution_plan(
    gateway: McpGateway,
    problem_id: str,
    plan: SolutionPlan,
) -> None:
    """Require exact solution, answer, and optional asset-target readback."""

    verified = normalized_content(gateway.get_problem_context(problem_id))
    solution = _section(verified, "solution")
    if solution is None or not _html_semantically_equal(
        str(solution.get("html") or ""),
        plan.solution_html,
    ):
        raise SolutionRuntimeError("solution readback differs from deterministic plan")
    for target_id, source_asset_id in plan.asset_target_ids:
        asset_context = gateway.get_problem_asset_target_context(
            problem_id,
            target_id,
        )
        if str(asset_context.get("current_asset_id") or "") != source_asset_id:
            raise SolutionRuntimeError("solution asset target points to another asset")
    answer = _section(verified, "answer")
    if answer is None or str(answer.get("html") or "") != plan.answer_html:
        raise AnswerVerificationError("answer readback differs from verified area")


def content_matches_plan(content: dict[str, Any], plan: SolutionPlan) -> bool:
    """Return whether both deterministic sections already match exactly."""

    solution = _section(content, "solution")
    answer = _section(content, "answer")
    return bool(
        solution is not None
        and answer is not None
        and _html_semantically_equal(
            str(solution.get("html") or ""),
            plan.solution_html,
        )
        and str(answer.get("html") or "") == plan.answer_html
    )


def _html_semantically_equal(actual: str, expected: str) -> bool:
    """Compare HTML after parser-level canonicalization."""

    return BeautifulSoup(actual, "html.parser").decode(
        formatter="minimal"
    ) == BeautifulSoup(expected, "html.parser").decode(formatter="minimal")


def existing_solution_asset(
    content: dict[str, Any],
    asset_key: str,
    expected_sha256: str,
) -> dict[str, str] | None:
    """Reuse one generated asset only when its exact digest is in readback."""

    matches = [
        asset
        for asset in content.get("assets", [])
        if isinstance(asset, dict) and asset.get("asset_key") == asset_key
    ]
    if len(matches) != 1:
        return None
    asset = matches[0]
    asset_id = str(asset.get("asset_id") or "")
    if not asset_id or str(asset.get("sha256") or "").lower() != expected_sha256:
        return None
    return {
        "source_asset_id": asset_id,
        "url": str(asset.get("url") or f"/assets/{asset_id}"),
        "sha256": expected_sha256,
    }
