"""Build the dashboard's read-only local index for one source group."""

from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from threading import Lock
from typing import Any, Callable, Mapping

from solution_runner.group_inventory_store import (
    GroupInventoryAsset,
    GroupInventoryItem,
    GroupInventorySnapshot,
    GroupInventoryStore,
)


class GroupInitializationError(RuntimeError):
    """Report invalid or incomplete source inventory data."""


@dataclass(frozen=True)
class _GroupSource:
    catalog_snapshot_id: str
    source_group_id: str


def _items(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        values = payload
    elif isinstance(payload, dict):
        values = payload.get("items", payload.get("children"))
    else:
        values = None
    if not isinstance(values, list):
        raise GroupInitializationError("source group children response has no item list")
    if not all(isinstance(value, dict) for value in values):
        raise GroupInitializationError("source group contains an invalid child")
    return values


def _identity(child: Mapping[str, Any]) -> tuple[str, str]:
    problem_id = str(child.get("uuid") or child.get("id") or "").strip()
    source_problem_id = str(child.get("source_problem_id") or "").strip()
    if not source_problem_id:
        name = str(child.get("name") or "").strip()
        source_problem_id = name.removeprefix("Задача ").strip()
    if not problem_id or not source_problem_id:
        raise GroupInitializationError("source problem has no stable identity")
    return problem_id, source_problem_id


def _normalized(context: Any) -> dict[str, Any]:
    if not isinstance(context, dict):
        raise GroupInitializationError("problem context is invalid")
    value = context.get("normalized_content")
    if not isinstance(value, dict):
        raise GroupInitializationError("problem has no normalized content")
    return value


def _sections(content: Mapping[str, Any]) -> list[dict[str, Any]]:
    values = content.get("sections", [])
    if isinstance(values, dict):
        return [dict(value, key=key) if isinstance(value, dict) else {"key": key}
                for key, value in values.items()]
    if not isinstance(values, list):
        return []
    return [value for value in values if isinstance(value, dict)]


def _section_key(section: Mapping[str, Any]) -> str:
    value = str(section.get("key") or section.get("section_id") or "").lower()
    for key in ("condition", "solution", "answer"):
        if value == key or value.startswith(f"{key}:"):
            return key
    return value


def _content_type(metadata: Any) -> str:
    if not isinstance(metadata, dict):
        return ""
    return str(metadata.get("content_type") or "").split(";", 1)[0].strip().lower()


def _batched_contexts(
    gateway: Any, problem_ids: list[str]
) -> tuple[dict[str, dict[str, Any]], dict[str, str], set[str]]:
    batch_reader = getattr(gateway, "get_problem_batch", None)
    if not callable(batch_reader):
        contexts: dict[str, dict[str, Any]] = {}
        errors: dict[str, str] = {}
        for problem_id in problem_ids:
            try:
                contexts[problem_id] = _normalized(gateway.get_problem_context(problem_id))
            except Exception as exc:  # noqa: BLE001 - one unavailable task is local.
                errors[problem_id] = " ".join(str(exc).split())[:500]
        return contexts, errors, set()
    contexts: dict[str, dict[str, Any]] = {}
    errors: dict[str, str] = {}
    rejected: set[str] = set()

    def read(requested: list[str]) -> None:
        try:
            payload = batch_reader(requested)
        except Exception as exc:  # noqa: BLE001 - isolate the unavailable member.
            if len(requested) > 1:
                middle = len(requested) // 2
                read(requested[:middle])
                read(requested[middle:])
            else:
                problem_id = requested[0]
                state_reader = getattr(gateway, "get_problem_pipeline_state", None)
                state = state_reader(problem_id) if callable(state_reader) else {}
                statuses = state.get("statuses") if isinstance(state, dict) else None
                normalized = str(statuses.get("normalized") or "") if isinstance(statuses, dict) else ""
                if normalized == "rejected":
                    rejected.add(problem_id)
                else:
                    errors[problem_id] = " ".join(str(exc).split())[:500]
            return
        rows = payload.get("items") if isinstance(payload, dict) else None
        if not isinstance(rows, list):
            raise GroupInitializationError("problem batch response has no item list")
        for row in rows:
            problem_id = str(row.get("problem_id") or "") if isinstance(row, dict) else ""
            if problem_id:
                contexts[problem_id] = _normalized(row)
        for problem_id in set(requested) - contexts.keys():
            errors[problem_id] = "problem batch response omitted this task"

    for offset in range(0, len(problem_ids), 30):
        read(problem_ids[offset:offset + 30])
    return contexts, errors, rejected


def _group_image_types(gateway: Any, source_group_id: str) -> dict[tuple[str, str, str, str], str]:
    reader = getattr(gateway, "get_source_catalog_section_images", None)
    if not callable(reader):
        return {}
    payload = reader(source_group_id, "group")
    result: dict[tuple[str, str, str, str], str] = {}
    for section_key in ("condition", "solution"):
        bucket = payload.get(section_key) if isinstance(payload, dict) else None
        rows = bucket.get("problems") if isinstance(bucket, dict) else None
        if not isinstance(rows, list):
            raise GroupInitializationError("section image response is invalid")
        for row in rows:
            source_problem_id = str(row.get("source_problem_id") or "")
            images = row.get("images") if isinstance(row, dict) else None
            for image in images if isinstance(images, list) else ():
                if not isinstance(image, dict):
                    continue
                asset_id = str(image.get("asset_id") or "")
                asset_key = str(image.get("asset_key") or "")
                if source_problem_id and asset_id and asset_key:
                    result[(source_problem_id, section_key, asset_key, asset_id)] = _content_type(image)
    return result


class GroupInitializer:
    """Populate one local index without writing to TeacherHelper."""

    def __init__(
        self,
        *,
        profiles: Mapping[str, Any],
        inventory_store: GroupInventoryStore,
        gateway_factory: Callable[[], Any],
        group_source_lookup: Callable[[str], Mapping[str, Any] | None] | None = None,
        on_complete: Callable[[str, Mapping[str, Any]], None] | None = None,
    ) -> None:
        self.profiles = profiles
        self.inventory_store = inventory_store
        self.gateway_factory = gateway_factory
        self.group_source_lookup = group_source_lookup
        self.on_complete = on_complete
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._futures: dict[str, Future[dict[str, Any]]] = {}
        self._lock = Lock()

    def _source(self, group_key: str, gateway: Any | None = None) -> _GroupSource:
        profile = self.profiles.get(group_key)
        if profile is not None:
            return _GroupSource(
                catalog_snapshot_id=str(profile.catalog_snapshot_id),
                source_group_id=str(profile.source_group_id),
            )
        group = self.group_source_lookup(group_key) if self.group_source_lookup else None
        catalog_id = str(group.get("source_id") or "").strip() if group else ""
        if not catalog_id:
            raise GroupInitializationError(f"group {group_key} has no source coordinates")
        if gateway is None:
            return _GroupSource(catalog_snapshot_id=catalog_id, source_group_id="")
        resolved = gateway.find_source_catalog_path(catalog_id, group_key, "group")
        target = resolved.get("target") if isinstance(resolved, dict) else None
        source_group_id = str(target.get("id") or "").strip() if isinstance(target, dict) else ""
        if not source_group_id:
            raise GroupInitializationError(f"group {group_key} was not found in catalog")
        return _GroupSource(catalog_snapshot_id=catalog_id, source_group_id=source_group_id)

    def start(self, group_key: str) -> dict[str, Any]:
        with self._lock:
            future = self._futures.get(group_key)
            if future is not None and not future.done():
                return self.get(group_key)
            self._source(group_key)
            self.inventory_store.set_status(group_key, "pending")
            self._futures[group_key] = self._executor.submit(self.run_now, group_key)
        return self.get(group_key)

    def get(self, group_key: str) -> dict[str, Any]:
        snapshot = self.inventory_store.get(group_key)
        if snapshot is None:
            return {"group_id": group_key, "status": "not_started", "error": None, "total": 0}
        return {
            "group_id": group_key,
            "status": snapshot.status,
            "error": snapshot.error,
            "total": len(snapshot.items),
            "assets": len(snapshot.assets),
            "unavailable": sum(
                item.content_status != "available" for item in snapshot.items
            ),
            "rejected": 0,
        }

    def run_now(self, group_key: str) -> dict[str, Any]:
        gateway = self.gateway_factory()
        self.inventory_store.set_status(group_key, "running")
        try:
            source = self._source(group_key, gateway)
            children = _items(
                gateway.get_source_catalog_children(source.source_group_id, "group")
            )
            if not children:
                raise GroupInitializationError("source group has no problems")
            identities = [_identity(child) for child in children]
            problem_ids = [problem_id for problem_id, _ in identities]
            if len(problem_ids) != len(set(problem_ids)):
                raise GroupInitializationError("source group contains duplicate problem ids")

            contexts, context_errors, rejected_problem_ids = _batched_contexts(
                gateway, problem_ids
            )
            group_image_types = _group_image_types(gateway, source.source_group_id)
            metadata_by_id: dict[str, dict[str, Any]] = {}
            inventory_items: list[GroupInventoryItem] = []
            inventory_assets: list[GroupInventoryAsset] = []

            for position, (problem_id, source_problem_id) in enumerate(identities):
                if problem_id in rejected_problem_ids:
                    continue
                content = contexts.get(problem_id, {})
                sections = _sections(content)
                section_keys = {_section_key(section) for section in sections}
                asset_sections = {
                    str(asset_key): _section_key(section)
                    for section in sections
                    for asset_key in section.get("asset_keys", [])
                }
                inventory_items.append(
                    GroupInventoryItem(
                        problem_id=problem_id,
                        source_problem_id=source_problem_id,
                        position=position,
                        has_condition="condition" in section_keys,
                        has_solution="solution" in section_keys,
                        has_answer="answer" in section_keys,
                        content_status=(
                            "unavailable" if problem_id in context_errors else "available"
                        ),
                        inventory_error=context_errors.get(problem_id),
                    )
                )
                assets = content.get("assets", [])
                if not isinstance(assets, list):
                    raise GroupInitializationError(
                        f"task {source_problem_id} has an invalid asset list"
                    )
                for asset in assets:
                    if not isinstance(asset, dict):
                        continue
                    asset_id = str(asset.get("asset_id") or "").strip()
                    asset_key = str(asset.get("asset_key") or "").strip()
                    section_key = asset_sections.get(asset_key, "")
                    if not asset_id or not asset_key or not section_key:
                        continue
                    content_type = group_image_types.get(
                        (source_problem_id, section_key, asset_key, asset_id), ""
                    )
                    if not content_type and asset_id not in metadata_by_id:
                        metadata = gateway.get_asset_metadata(asset_id)
                        metadata_by_id[asset_id] = metadata if isinstance(metadata, dict) else {}
                    inventory_assets.append(
                        GroupInventoryAsset(
                            problem_id=problem_id,
                            asset_id=asset_id,
                            asset_key=asset_key,
                            section_key=section_key,
                            content_type=content_type or _content_type(metadata_by_id[asset_id]),
                        )
                    )

            parent = next(
                (identity for identity in identities if identity[0] not in rejected_problem_ids),
                ("", ""),
            )
            parent_problem_id, parent_source_problem_id = parent
            self.inventory_store.replace(
                GroupInventorySnapshot(
                    group_key=group_key,
                    catalog_snapshot_id=source.catalog_snapshot_id,
                    source_group_id=source.source_group_id,
                    parent_problem_id=parent_problem_id,
                    parent_source_problem_id=parent_source_problem_id,
                    items=tuple(inventory_items),
                    assets=tuple(inventory_assets),
                )
            )
        except Exception as exc:  # noqa: BLE001 - persist a concise group-level failure.
            error = " ".join(str(exc).split())[:500]
            self.inventory_store.set_status(group_key, "failed", error)
        finally:
            close = getattr(gateway, "close", None)
            if callable(close):
                close()
        state = self.get(group_key)
        state["rejected"] = len(rejected_problem_ids) if "rejected_problem_ids" in locals() else 0
        if self.on_complete:
            self.on_complete(group_key, state)
        return state
