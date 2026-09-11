"""Read and cache one parent/result preview per registered group."""

from __future__ import annotations

import argparse
from copy import deepcopy
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping

from bs4 import BeautifulSoup

from solution_runner.pipelines.core.group_profiles import all_group_profiles
from solution_runner.pipelines.grid_polygon.mcp_runtime import (
    DEFAULT_MCP_URL,
    JsonRpcMcpGateway,
)

ASSET_BASE_URL = "https://lessons-helper.ru"
ALLOWED_ATTRIBUTES = {
    "alt", "class", "colspan", "data-align", "data-asset-id", "data-asset-key",
    "data-cell-tone", "data-formula-render-mode", "data-inline-latex",
    "data-solution-title", "data-valign", "height", "href", "rowspan", "src",
    "title", "width",
}


class ProblemPreviewUnavailable(ValueError):
    """The requested problem must not be opened in the dashboard."""


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _problem_id(item: Mapping[str, Any]) -> str:
    value = item.get("uuid") or item.get("problem_id") or item.get("id")
    if not value:
        raise ValueError("problem identity is missing")
    return str(value)


def _source_problem_id(item: Mapping[str, Any]) -> str:
    value = item.get("source_problem_id")
    if value:
        return str(value)
    name = str(item.get("name") or "")
    return name.removeprefix("Задача ").strip() or _problem_id(item)


def _safe_html(html: str, assets: Mapping[str, str]) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup.find_all(("script", "style", "iframe", "object", "embed")):
        tag.decompose()
    for tag in soup.find_all(True):
        for attribute in list(tag.attrs):
            if attribute.lower().startswith("on") or attribute not in ALLOWED_ATTRIBUTES:
                del tag.attrs[attribute]
        if tag.has_attr("src"):
            source = str(tag.get("src") or "")
            if not source.startswith(("https://", "http://", "/")):
                del tag.attrs["src"]
        if tag.name == "img":
            key = str(tag.get("data-asset-key") or "")
            if key in assets:
                tag["src"] = assets[key]
    body = soup.body
    return "".join(str(node) for node in (body.contents if body else soup.contents))


def _card(item: Mapping[str, Any], content: Any) -> dict[str, Any]:
    if not isinstance(content, dict):
        raise ValueError("problem content is missing")
    assets = {}
    for asset in content.get("assets") or []:
        if not isinstance(asset, dict):
            continue
        key = str(asset.get("asset_key") or "")
        url = str(asset.get("url") or asset.get("source_url") or "")
        if key and url.startswith("/assets/"):
            assets[key] = ASSET_BASE_URL + url
        elif key and url.startswith(("https://", "http://")):
            assets[key] = url
    sections = {}
    for section in content.get("sections") or []:
        if not isinstance(section, dict):
            continue
        key = str(section.get("key") or section.get("section_id") or "").split(":", 1)[0]
        if key in {"condition", "solution", "answer"} and key not in sections:
            sections[key] = _safe_html(str(section.get("html") or ""), assets)
    return {
        "problem_id": _problem_id(item),
        "source_problem_id": _source_problem_id(item),
        "condition_html": sections.get("condition", ""),
        "solution_html": sections.get("solution", ""),
        "answer_html": sections.get("answer", ""),
    }


def fetch_problem_preview(
    gateway: Any,
    preview_dir: Path,
    group_key: str,
    problem_id: str,
    source_problem_id: str,
) -> dict[str, Any]:
    """Return a saved comparison or a read-only normalized card for one task."""

    cached = load_preview(preview_dir, group_key)
    if cached:
        sample = next(
            (
                item for item in cached.get("samples", [])
                if isinstance(item, dict) and str(item.get("problem_id")) == problem_id
            ),
            None,
        )
        if sample:
            return {"group_key": group_key, "fetched_at": cached.get("fetched_at"), "samples": [sample]}

    context = gateway.get_problem_context(problem_id)
    normalized = context.get("normalized_content") if isinstance(context, dict) else None
    if not isinstance(normalized, dict):
        raise ProblemPreviewUnavailable("normalized content is unavailable")
    item = {"problem_id": problem_id, "source_problem_id": source_problem_id}
    return {
        "group_key": group_key,
        "fetched_at": _now(),
        "samples": [{
            "problem_id": problem_id,
            "source_problem_id": source_problem_id,
            "before": _card(item, normalized),
            "after": None,
            "fetched_at": _now(),
        }],
    }


def _apply_locally(content: Mapping[str, Any], transformations: list[dict[str, Any]]) -> dict[str, Any]:
    """Materialize a dry-run plan in memory without an MCP write."""

    result = deepcopy(dict(content))
    sections = result.setdefault("sections", [])
    assets = result.setdefault("assets", [])
    for transformation in transformations:
        target_id = str(transformation.get("transformation_target_id") or "")
        operation = transformation.get("operation")
        value = transformation.get("value")
        if target_id.startswith("section:"):
            match = next((section for section in sections if section.get("transformation_target_id") == target_id), None)
            if operation == "remove":
                sections[:] = [section for section in sections if section is not match]
            elif operation in {"add", "rewrite"} and isinstance(value, dict):
                updates = {
                    key: deepcopy(item)
                    for key, item in value.items()
                    if key in {"html", "title", "asset_keys"}
                }
                if match is None and operation == "add":
                    sections.append({
                        "key": target_id.split(":", 2)[1],
                        "transformation_target_id": target_id,
                        **updates,
                    })
                elif match is not None:
                    match.update(updates)
        elif target_id.startswith("asset:"):
            key = target_id.split(":", 1)[1]
            if operation == "remove":
                assets[:] = [asset for asset in assets if asset.get("asset_key") != key]
            elif operation in {"add", "rewrite"} and isinstance(value, dict):
                match = next((asset for asset in assets if asset.get("asset_key") == key), None)
                if match is None:
                    assets.append(deepcopy(value))
                else:
                    match.update(deepcopy(value))
    return result


def _sample(gateway: Any, record: Mapping[str, Any]) -> dict[str, Any]:
    item = {
        "problem_id": record.get("problem_id"),
        "source_problem_id": record.get("source_problem_id"),
    }
    context = gateway.get_problem_context(_problem_id(item))
    before_content = context.get("normalized_content")
    if not isinstance(before_content, dict):
        raise ValueError("normalized content is missing")
    transformations = record.get("transformations")
    if not isinstance(transformations, list):
        raise ValueError("dry-run record has no transformations")
    before = _card(item, before_content)
    after = _card(item, _apply_locally(before_content, transformations))
    return {
        "problem_id": _problem_id(item),
        "source_problem_id": _source_problem_id(item),
        "before": before,
        "after": after,
        "fetched_at": _now(),
    }


def _manifest_group(payload: Mapping[str, Any]) -> str:
    return str(payload.get("group_key") or (payload.get("scope") or {}).get("group_key") or "")


def _preview_records(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        record
        for record in payload.get("records", [])
        if isinstance(record, dict)
        and record.get("status") != "blocked"
        and record.get("problem_id")
        and isinstance(record.get("transformations"), list)
    ]


def _with_solution_plans(manifest_path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    """Attach geometry plans persisted by the solution stage to prepared records."""

    results_path = manifest_path.parent / "solution-results.json"
    try:
        results = json.loads(results_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return payload
    if not isinstance(results, list):
        return payload
    plans = {
        str(result.get("problem_id")): result.get("transformations")
        for result in results
        if isinstance(result, dict)
        and result.get("status") in {"planned", "already_complete"}
        and isinstance(result.get("transformations"), list)
    }
    if not plans:
        return payload
    merged = deepcopy(payload)
    for record in merged.get("records", []):
        if isinstance(record, dict) and str(record.get("problem_id")) in plans:
            record["transformations"] = deepcopy(plans[str(record.get("problem_id"))])
    return merged


def latest_dry_run_manifest(var_dir: Path, group_key: str) -> dict[str, Any] | None:
    """Return the newest usable dry-run, including one already applied.

    A preview is an audit artifact: recording its plan through Apply must not
    make the before/after comparison disappear from the dashboard.
    """

    manifests = list(var_dir.glob(f"**/runs/*-group-{group_key}/prepared-manifest.json"))
    for manifest in sorted(manifests, key=lambda path: path.stat().st_mtime, reverse=True):
        try:
            payload = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        payload = _with_solution_plans(manifest, payload)
        if _manifest_group(payload) == group_key and _preview_records(payload):
            return payload
    return None


def fetch_preview(gateway: Any, profile: Any, manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Freeze one normalized-input/local-output pair from a current dry-run."""

    records = _preview_records(manifest)
    if not records:
        raise ValueError("dry-run has no preview candidates")
    return {
        "group_key": profile.group_key,
        "fetched_at": _now(),
        "samples": [_sample(gateway, records[0])],
    }


def append_preview_sample(
    gateway: Any,
    profile: Any,
    preview_dir: Path,
    var_dir: Path,
    *,
    source_problem_id: str | None = None,
) -> dict[str, Any]:
    """Add one requested or next unused child to a group's cached review samples."""

    manifest = latest_dry_run_manifest(var_dir, profile.group_key)
    if manifest is None:
        raise ValueError("no current dry-run found")
    payload = load_preview(preview_dir, profile.group_key) or fetch_preview(gateway, profile, manifest)
    items = _preview_records(manifest)
    existing = {str(item.get("problem_id")) for item in payload.get("samples", [])}
    candidates = [item for item in items if _problem_id(item) not in existing]
    if source_problem_id:
        candidates = [
            item for item in candidates
            if source_problem_id in {_problem_id(item), _source_problem_id(item)}
        ]
    if not candidates:
        raise ValueError("no unused preview task found")
    payload.setdefault("samples", []).append(_sample(gateway, candidates[0]))
    payload["fetched_at"] = _now()
    save_preview(preview_dir, payload)
    return payload


def preview_path(preview_dir: Path, group_key: str) -> Path:
    return preview_dir / f"{group_key}.json"


def save_preview(preview_dir: Path, payload: Mapping[str, Any]) -> Path:
    preview_dir.mkdir(parents=True, exist_ok=True)
    target = preview_path(preview_dir, str(payload["group_key"]))
    temporary = target.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    temporary.replace(target)
    return target


def load_preview(preview_dir: Path, group_key: str) -> dict[str, Any] | None:
    try:
        payload = json.loads(preview_path(preview_dir, group_key).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _fetch_one(group_key: str, profile: Any, preview_dir: Path, var_dir: Path) -> tuple[str, str]:
    manifest = latest_dry_run_manifest(var_dir, group_key)
    if manifest is None:
        preview_path(preview_dir, group_key).unlink(missing_ok=True)
        return group_key, "no_current_dry_run"
    gateway = JsonRpcMcpGateway(
        url=os.environ.get("TEACHERHELPER_MCP_URL", DEFAULT_MCP_URL),
        api_key=os.environ["TEACHERHELPER_MCP_API_KEY"],
        timeout_seconds=45,
    )
    try:
        save_preview(preview_dir, fetch_preview(gateway, profile, manifest))
        return group_key, "ok"
    except Exception as exc:  # noqa: BLE001 - one group must not block the backfill.
        return group_key, " ".join(str(exc).split())[:300]
    finally:
        gateway.close()


def backfill_previews(preview_dir: Path, var_dir: Path, profiles: Mapping[str, Any], *, workers: int = 4) -> dict[str, Any]:
    results: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=max(1, min(workers, 6))) as executor:
        futures = {
            executor.submit(_fetch_one, key, profile, preview_dir, var_dir): key
            for key, profile in profiles.items()
        }
        for future in as_completed(futures):
            key, status = future.result()
            results[key] = status
            print(f"{len(results)}/{len(futures)} {key}: {status}", flush=True)
    return {
        "total": len(results),
        "ready": sum(value == "ok" for value in results.values()),
        "without_dry_run": sum(value == "no_current_dry_run" for value in results.values()),
        "errors": {key: value for key, value in results.items() if value not in {"ok", "no_current_dry_run"}},
    }


def main(argv: list[str] | None = None) -> int:
    root = Path(__file__).resolve().parents[3]
    parser = argparse.ArgumentParser(description="Backfill one real preview per registered group")
    parser.add_argument("--dir", type=Path, default=root / "var/dashboard/previews")
    parser.add_argument("--var", type=Path, default=root / "var")
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args(argv)
    if not os.environ.get("TEACHERHELPER_MCP_API_KEY"):
        parser.error("TEACHERHELPER_MCP_API_KEY is required")
    report = backfill_previews(args.dir, args.var, all_group_profiles(), workers=args.workers)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not report["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
