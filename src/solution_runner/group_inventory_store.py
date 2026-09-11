"""Persist the read-only local index of one source problem group."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3


@dataclass(frozen=True)
class GroupInventoryItem:
    problem_id: str
    source_problem_id: str
    position: int
    has_condition: bool
    has_solution: bool
    has_answer: bool
    content_status: str = "available"
    inventory_error: str | None = None


@dataclass(frozen=True)
class GroupInventoryAsset:
    problem_id: str
    asset_id: str
    asset_key: str
    section_key: str
    content_type: str


@dataclass(frozen=True)
class GroupInventorySnapshot:
    group_key: str
    catalog_snapshot_id: str
    source_group_id: str
    parent_problem_id: str
    parent_source_problem_id: str
    items: tuple[GroupInventoryItem, ...] = ()
    assets: tuple[GroupInventoryAsset, ...] = ()
    status: str = "ready"
    error: str | None = None


@dataclass(frozen=True)
class GroupItemStageResult:
    group_key: str
    problem_id: str
    dry_run_status: str | None = None
    apply_status: str | None = None
    helpers_status: str | None = None
    error: str | None = None


SCHEMA = """
CREATE TABLE IF NOT EXISTS group_inventories (
    group_key TEXT PRIMARY KEY,
    catalog_snapshot_id TEXT NOT NULL DEFAULT '',
    source_group_id TEXT NOT NULL DEFAULT '',
    parent_problem_id TEXT NOT NULL DEFAULT '',
    parent_source_problem_id TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'pending',
    error TEXT
);
CREATE TABLE IF NOT EXISTS group_inventory_items (
    group_key TEXT NOT NULL,
    problem_id TEXT NOT NULL,
    source_problem_id TEXT NOT NULL,
    position INTEGER NOT NULL,
    has_condition INTEGER NOT NULL,
    has_solution INTEGER NOT NULL,
    has_answer INTEGER NOT NULL,
    content_status TEXT NOT NULL DEFAULT 'available',
    inventory_error TEXT,
    PRIMARY KEY (group_key, problem_id),
    FOREIGN KEY (group_key) REFERENCES group_inventories(group_key) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS group_inventory_assets (
    group_key TEXT NOT NULL,
    problem_id TEXT NOT NULL,
    asset_id TEXT NOT NULL,
    asset_key TEXT NOT NULL,
    section_key TEXT NOT NULL,
    content_type TEXT NOT NULL,
    PRIMARY KEY (group_key, problem_id, asset_id, section_key),
    FOREIGN KEY (group_key, problem_id)
        REFERENCES group_inventory_items(group_key, problem_id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS group_item_stage_results (
    group_key TEXT NOT NULL,
    problem_id TEXT NOT NULL,
    dry_run_status TEXT,
    dry_run_error TEXT,
    apply_status TEXT,
    apply_error TEXT,
    helpers_status TEXT,
    error TEXT,
    PRIMARY KEY (group_key, problem_id)
);
"""


class GroupInventoryStore:
    """Own the local source-group index without storing problem content."""

    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.executescript(SCHEMA)
            columns = {
                row["name"] for row in connection.execute(
                    "PRAGMA table_info(group_inventory_items)"
                ).fetchall()
            }
            if "content_status" not in columns:
                connection.execute(
                    "ALTER TABLE group_inventory_items "
                    "ADD COLUMN content_status TEXT NOT NULL DEFAULT 'available'"
                )
            if "inventory_error" not in columns:
                connection.execute(
                    "ALTER TABLE group_inventory_items ADD COLUMN inventory_error TEXT"
                )
            stage_columns = {
                row["name"] for row in connection.execute(
                    "PRAGMA table_info(group_item_stage_results)"
                ).fetchall()
            }
            for name in ("dry_run_error", "apply_error"):
                if name not in stage_columns:
                    connection.execute(
                        f"ALTER TABLE group_item_stage_results ADD COLUMN {name} TEXT"
                    )
            connection.execute(
                """
                UPDATE group_item_stage_results
                SET apply_error = error
                WHERE apply_error IS NULL AND error IS NOT NULL
                  AND (apply_status IS NOT NULL OR helpers_status IS NOT NULL)
                """
            )

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def replace(self, snapshot: GroupInventorySnapshot) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO group_inventories (
                    group_key, catalog_snapshot_id, source_group_id,
                    parent_problem_id, parent_source_problem_id, status, error
                ) VALUES (?, ?, ?, ?, ?, 'ready', NULL)
                ON CONFLICT(group_key) DO UPDATE SET
                    catalog_snapshot_id=excluded.catalog_snapshot_id,
                    source_group_id=excluded.source_group_id,
                    parent_problem_id=excluded.parent_problem_id,
                    parent_source_problem_id=excluded.parent_source_problem_id,
                    status='ready', error=NULL
                """,
                (
                    snapshot.group_key,
                    snapshot.catalog_snapshot_id,
                    snapshot.source_group_id,
                    snapshot.parent_problem_id,
                    snapshot.parent_source_problem_id,
                ),
            )
            connection.execute(
                "DELETE FROM group_inventory_assets WHERE group_key = ?",
                (snapshot.group_key,),
            )
            connection.execute(
                "DELETE FROM group_inventory_items WHERE group_key = ?",
                (snapshot.group_key,),
            )
            connection.executemany(
                """
                INSERT INTO group_inventory_items (
                    group_key, problem_id, source_problem_id, position,
                    has_condition, has_solution, has_answer
                    , content_status, inventory_error
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        snapshot.group_key,
                        item.problem_id,
                        item.source_problem_id,
                        item.position,
                        item.has_condition,
                        item.has_solution,
                        item.has_answer,
                        item.content_status,
                        item.inventory_error,
                    )
                    for item in snapshot.items
                ],
            )
            connection.executemany(
                """
                INSERT INTO group_inventory_assets (
                    group_key, problem_id, asset_id, asset_key, section_key,
                    content_type
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        snapshot.group_key,
                        asset.problem_id,
                        asset.asset_id,
                        asset.asset_key,
                        asset.section_key,
                        asset.content_type,
                    )
                    for asset in snapshot.assets
                ],
            )
            problem_ids = [item.problem_id for item in snapshot.items]
            if problem_ids:
                placeholders = ",".join("?" for _ in problem_ids)
                connection.execute(
                    f"DELETE FROM group_item_stage_results WHERE group_key = ? "
                    f"AND problem_id NOT IN ({placeholders})",
                    (snapshot.group_key, *problem_ids),
                )
            else:
                connection.execute(
                    "DELETE FROM group_item_stage_results WHERE group_key = ?",
                    (snapshot.group_key,),
                )

    def set_status(self, group_key: str, status: str, error: str | None = None) -> None:
        if status not in {"pending", "running", "partial", "ready", "failed"}:
            raise ValueError("invalid inventory status")
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO group_inventories (group_key, status, error)
                VALUES (?, ?, ?)
                ON CONFLICT(group_key) DO UPDATE SET
                    status=excluded.status, error=excluded.error
                """,
                (group_key, status, error),
            )

    def get(self, group_key: str) -> GroupInventorySnapshot | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM group_inventories WHERE group_key = ?", (group_key,)
            ).fetchone()
            if row is None:
                return None
            item_rows = connection.execute(
                "SELECT * FROM group_inventory_items WHERE group_key = ? ORDER BY position",
                (group_key,),
            ).fetchall()
            asset_rows = connection.execute(
                """SELECT * FROM group_inventory_assets
                   WHERE group_key = ? ORDER BY problem_id, section_key, asset_key""",
                (group_key,),
            ).fetchall()
        return GroupInventorySnapshot(
            group_key=row["group_key"],
            catalog_snapshot_id=row["catalog_snapshot_id"],
            source_group_id=row["source_group_id"],
            parent_problem_id=row["parent_problem_id"],
            parent_source_problem_id=row["parent_source_problem_id"],
            items=tuple(
                GroupInventoryItem(
                    item["problem_id"],
                    item["source_problem_id"],
                    item["position"],
                    bool(item["has_condition"]),
                    bool(item["has_solution"]),
                    bool(item["has_answer"]),
                    item["content_status"],
                    item["inventory_error"],
                )
                for item in item_rows
            ),
            assets=tuple(
                GroupInventoryAsset(
                    asset["problem_id"],
                    asset["asset_id"],
                    asset["asset_key"],
                    asset["section_key"],
                    asset["content_type"],
                )
                for asset in asset_rows
            ),
            status=row["status"],
            error=row["error"],
        )

    def update_item_stage(self, result: GroupItemStageResult) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO group_item_stage_results (
                    group_key, problem_id, dry_run_status, apply_status,
                    helpers_status, error, dry_run_error, apply_error
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(group_key, problem_id) DO UPDATE SET
                    dry_run_status=COALESCE(excluded.dry_run_status, dry_run_status),
                    dry_run_error=CASE
                        WHEN excluded.dry_run_status IS NOT NULL THEN excluded.dry_run_error
                        ELSE dry_run_error
                    END,
                    apply_status=COALESCE(excluded.apply_status, apply_status),
                    apply_error=CASE
                        WHEN excluded.apply_status IS NULL AND excluded.helpers_status IS NULL THEN apply_error
                        WHEN ? THEN NULL
                        WHEN excluded.apply_error IS NOT NULL THEN excluded.apply_error
                        ELSE apply_error
                    END,
                    helpers_status=COALESCE(excluded.helpers_status, helpers_status),
                    error=CASE
                        WHEN ? THEN NULL
                        WHEN excluded.apply_status IS NULL
                             AND excluded.helpers_status = 'skipped'
                             AND excluded.error LIKE 'ineligible upstream %'
                        THEN error
                        WHEN excluded.error IS NOT NULL THEN excluded.error
                        ELSE error
                    END
                """,
                (
                    result.group_key,
                    result.problem_id,
                    result.dry_run_status,
                    result.apply_status,
                    result.helpers_status,
                    result.error,
                    result.error if result.dry_run_status is not None else None,
                    result.error if result.apply_status is not None or result.helpers_status is not None else None,
                    result.error is None and result.helpers_status in {
                        "applied", "already_complete"
                    },
                    result.error is None and result.helpers_status in {
                        "applied", "already_complete"
                    },
                ),
            )

    def remove_item(self, group_key: str, problem_id: str) -> None:
        with self.connect() as connection:
            connection.execute(
                "DELETE FROM group_inventory_items WHERE group_key = ? AND problem_id = ?",
                (group_key, problem_id),
            )
            connection.execute(
                "DELETE FROM group_item_stage_results WHERE group_key = ? AND problem_id = ?",
                (group_key, problem_id),
            )

    def list_items(self, group_key: str) -> list[dict[str, object]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT item.*, result.dry_run_status, result.dry_run_error,
                       result.apply_status, result.apply_error, result.helpers_status, result.error
                FROM group_inventory_items AS item
                LEFT JOIN group_item_stage_results AS result
                  ON result.group_key = item.group_key
                 AND result.problem_id = item.problem_id
                WHERE item.group_key = ?
                ORDER BY item.position
                """,
                (group_key,),
            ).fetchall()
        return [dict(row) for row in rows]
