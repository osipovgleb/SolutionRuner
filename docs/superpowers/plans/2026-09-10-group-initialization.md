# Group Initialization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Добавить разовую инициализацию группы в SQLite и позволить общему launcher использовать сохранённый состав задач без повторного inventory.

**Architecture:** Нейтральный `GroupInventoryStore` владеет тремя таблицами локального индекса и используется как дэшбордом, так и общим launcher. Последовательный `GroupInitializer` читает структуру и normalized metadata через MCP, атомарно заменяет индекс и переводит карточку из `Инициализация` в `На регистрацию`. Dashboard dry-run передаёт общему launcher путь к SQLite; старый MCP-inventory остаётся временным CLI fallback, пока существующие группы не инициализированы.

**Tech Stack:** Python 3.12 standard library (`sqlite3`, `http.server`, `ThreadPoolExecutor`), Preact/Vite, существующий JSON-RPC MCP gateway, pytest, Node test runner.

**Spec:** `docs/superpowers/specs/2026-09-10-group-dashboard-design.md`

## Global Constraints

- Один общий launcher; новые группы добавляют только обработчик и профиль.
- Никаких git worktree: вся работа выполняется в общем checkout проекта.
- Initialize хранит идентификаторы и метаданные секций/ассетов, но не HTML normalized content и не transformations.
- Новые SQL-имена используют `group`, `item`, `problem_id`, `source_problem_id` и `catalog_snapshot_id`; термины `family`, `cluster` и `block` запрещены.
- MCP-записи на этапе Initialize и dry-run запрещены.
- Ошибка Initialize остаётся в `Инициализации`; ошибка dry-run не переводит карточку в `Проблемы`; `Проблемы` зарезервированы для apply/readback.
- Автоматической переинициализации нет.

---

### Task 1: Локальный индекс группы в SQLite

**Files:**
- Create: `src/solution_runner/group_inventory_store.py`
- Test: `tests/test_group_inventory_store.py`

**Interfaces:**
- Produces: `GroupInventoryItem`, `GroupInventoryAsset`, `GroupInventorySnapshot`, `GroupItemStageResult` dataclasses.
- Produces: `GroupInventoryStore(path: Path)`, `replace(snapshot)`, `get(group_key)`, `set_status(group_key, status, error=None)`, `update_item_stage(result)`.
- Consumes: один и тот же путь SQLite, который использует dashboard.

- [ ] **Step 1: Write the failing atomic round-trip test**

```python
def test_replace_inventory_is_atomic_and_preserves_problem_id_names(tmp_path):
    store = GroupInventoryStore(tmp_path / "dashboard.sqlite3")
    snapshot = GroupInventorySnapshot(
        group_key="27591",
        catalog_snapshot_id="catalog",
        source_group_id="source-group",
        parent_problem_id="problem-parent",
        parent_source_problem_id="55259",
        items=(GroupInventoryItem("problem-parent", "55259", 0, True, True, True),),
        assets=(GroupInventoryAsset("problem-parent", "asset-1", "image_1", "condition", "image/svg+xml"),),
    )
    store.replace(snapshot)
    assert store.get("27591") == snapshot
```

- [ ] **Step 2: Run the focused test and verify RED**

Run: `.venv/bin/pytest -q tests/test_group_inventory_store.py`

Expected: FAIL because `solution_runner.group_inventory_store` does not exist.

- [ ] **Step 3: Implement the minimal schema and transaction**

Create plural tables `group_inventories`, `group_inventory_items`,
`group_inventory_assets` and `group_item_stage_results`. Use `(group_key,
problem_id)` and
`(group_key, problem_id, asset_id, section_key)` as stable composite keys.
`replace()` must start one SQLite transaction, delete the old child rows, insert
the new snapshot, and commit only after every row succeeds. It must not delete
stage results for problem IDs that remain in the refreshed group.

- [ ] **Step 4: Add status behavior**

Cover literal statuses `pending`, `running`, `ready`, `failed`. A failed refresh
updates status/error but retains the last ready item and asset rows.

- [ ] **Step 5: Run tests and commit**

Run: `.venv/bin/pytest -q tests/test_group_inventory_store.py`

```bash
git add src/solution_runner/group_inventory_store.py tests/test_group_inventory_store.py
git commit -m "feat: add local group inventory store"
```

---

### Task 2: Read-only MCP initializer

**Files:**
- Create: `src/solution_runner/dashboard/initialization.py`
- Test: `tests/dashboard/test_initialization.py`

**Interfaces:**
- Consumes: `GroupInventoryStore` from Task 1 and an existing `JsonRpcMcpGateway` factory.
- Produces: `GroupInitializer.start(group_key) -> dict`, `get(group_key) -> dict`.
- Produces: one serialized worker (`ThreadPoolExecutor(max_workers=1)`).

- [ ] **Step 1: Write the failing manifest test**

Use a complete fake MCP envelope with ordered `items`, three
`get_problem_context` responses and deduplicated `get_asset_metadata` responses.
Assert that the first item becomes the parent, order is retained, section flags
come only from `normalized_content.sections`, and PNG/SVG comes from the asset
`content_type`. Assert the fake has no write methods and no write call occurs.

- [ ] **Step 2: Verify RED**

Run: `.venv/bin/pytest -q tests/dashboard/test_initialization.py`

Expected: FAIL because `GroupInitializer` is undefined.

- [ ] **Step 3: Implement one read path**

For one group profile:

1. call `get_source_catalog_children(source_group_id, "group")`;
2. validate unique `problem_id` and `source_problem_id` values;
3. fetch each problem context with at most three workers;
4. record only section-presence booleans and asset identities;
5. fetch metadata once per unique asset ID;
6. call `GroupInventoryStore.replace()` only after the entire snapshot validates.

On any exception call `set_status(group_key, "failed", concise_error)` and do
not erase the previous ready snapshot.

- [ ] **Step 4: Test serialization and no automatic retry**

Start two groups, hold the first fake gateway call, and assert the second remains
`pending` until the first completes. Assert a failed group stays `failed` until
another explicit `start()` call.

- [ ] **Step 5: Run tests and commit**

Run: `.venv/bin/pytest -q tests/dashboard/test_initialization.py tests/test_group_inventory_store.py`

```bash
git add src/solution_runner/dashboard/initialization.py tests/dashboard/test_initialization.py
git commit -m "feat: initialize group inventory through MCP"
```

---

### Task 3: Initialization column and API

**Files:**
- Modify: `src/solution_runner/dashboard/store.py`
- Modify: `src/solution_runner/dashboard/server.py`
- Modify: `dashboard/src/api.js`
- Modify: `dashboard/src/main.jsx`
- Modify: `dashboard/src/styles.css`
- Test: `tests/dashboard/test_store.py`
- Test: `tests/dashboard/test_server.py`
- Test: `dashboard/src/api.test.js`

**Interfaces:**
- Consumes: `GroupInitializer.start/get` from Task 2.
- Produces: `GET /api/groups/{group_key}/inventory` and `POST /api/groups/{group_key}/initialize`.
- Produces: kanban column ID `initialization` with visible title `Инициализация`.

- [ ] **Step 1: Write failing store and API tests**

Assert a newly added manual group has `column == "initialization"`. Assert POST
Initialize returns `202` and GET returns the persisted inventory status. Assert
PATCH accepts `initialization` and still rejects unknown columns.

- [ ] **Step 2: Verify RED**

Run: `.venv/bin/pytest -q tests/dashboard/test_store.py tests/dashboard/test_server.py`

- [ ] **Step 3: Implement the backend route and transition**

`POST /api/groups` creates the card in `initialization` and enqueues exactly one
Initialize. When status becomes `ready`, update the card to `queue`; on `failed`,
leave it in `initialization` and expose the concise error in the card panel.
Do not create or message a Codex task in this task.

- [ ] **Step 4: Add the sixth frontend column**

Add `Инициализация` before `На регистрацию`. Show counts while running and a
single `Повторить инициализацию` action only after failure or on explicit user
request. Do not start initialization from page load.

- [ ] **Step 5: Run backend/frontend tests and build**

Run: `.venv/bin/pytest -q tests/dashboard`

Run: `cd dashboard && npm test -- --run && npm run build`

- [ ] **Step 6: Commit**

```bash
git add src/solution_runner/dashboard dashboard/src tests/dashboard
git commit -m "feat: add group initialization workflow"
```

---

### Task 4: Common launcher reads the local group index

**Files:**
- Create: `src/solution_runner/pipelines/core/local_inventory.py`
- Modify: `src/solution_runner/pipelines/grid_polygon/launcher.py`
- Modify: `src/solution_runner/dashboard/dry_runs.py`
- Test: `tests/pipelines/core/test_local_inventory.py`
- Test: `tests/pipelines/grid_polygon/test_launcher.py`
- Test: `tests/dashboard/test_dry_runs.py`

**Interfaces:**
- Consumes: `GroupInventoryStore.get(group_key)` from Task 1.
- Produces: `load_local_inventory(db_path, profile, source_problem_ids=(), problem_ids=()) -> GroupInventory`.
- Produces: common launcher option `--inventory-db PATH`; no second launcher.

- [ ] **Step 1: Write failing reconstruction tests**

Create one ready inventory snapshot with a parent and two children. Assert
`load_local_inventory()` reconstructs ordered `ProblemTarget` rows, PNG/SVG
subsets and exact `--only-problem-id` selection without making gateway calls.
Assert missing, failed or mismatched group inventory raises `InventoryError`.

- [ ] **Step 2: Verify RED**

Run: `.venv/bin/pytest -q tests/pipelines/core/test_local_inventory.py`

- [ ] **Step 3: Add one optional inventory source to the common launcher**

When `--inventory-db` is present, call `load_local_inventory()` and never call
`discover_group_inventory()` or `discover_targeted_inventory()`. Without the
option, retain the current MCP-inventory path temporarily so existing CLI
commands keep working while groups are initialized.

- [ ] **Step 4: Make dashboard dry-runs pass the database path**

Extend `_launcher_command()` with exactly:

```python
command.extend(("--inventory-db", str(inventory_db_path)))
```

The path comes from the configured `DashboardStore`; no hard-coded home or
workspace path. Keep `--apply` absent.

- [ ] **Step 5: Verify launcher behavior**

Run: `.venv/bin/pytest -q tests/pipelines/core/test_local_inventory.py tests/pipelines/grid_polygon/test_launcher.py tests/dashboard/test_dry_runs.py`

Expected: all pass; tests assert zero MCP inventory calls on the local path.

- [ ] **Step 6: Commit**

```bash
git add src/solution_runner/pipelines/core/local_inventory.py src/solution_runner/pipelines/grid_polygon/launcher.py src/solution_runner/dashboard/dry_runs.py tests
git commit -m "feat: run registered groups from local inventory"
```

---

### Task 5: «Все задачи» and per-item stage results

**Files:**
- Modify: `src/solution_runner/group_inventory_store.py`
- Modify: `src/solution_runner/dashboard/server.py`
- Modify: `src/solution_runner/dashboard/dry_runs.py`
- Modify: `dashboard/src/main.jsx`
- Modify: `dashboard/src/styles.css`
- Test: `tests/test_group_inventory_store.py`
- Test: `tests/dashboard/test_server.py`
- Test: `tests/dashboard/test_dry_runs.py`

**Interfaces:**
- Consumes: inventory rows and `update_item_stage()` from Task 1.
- Produces: `GET /api/groups/{group_key}/items` returning inventory metadata joined with latest per-item results.
- Produces: frontend tab ID `items` with title `Все задачи`.

- [ ] **Step 1: Write failing joined-result tests**

Seed two inventory items and update only one with literal statuses
`dry_run_status="completed"`, `apply_status=None`, `helpers_status="ready"`.
Assert the API returns both items in source order and does not invent a status
for the untouched item. Replacing the inventory with the same problem IDs must
preserve the saved stage result.

- [ ] **Step 2: Verify RED**

Run: `.venv/bin/pytest -q tests/test_group_inventory_store.py tests/dashboard/test_server.py`

- [ ] **Step 3: Persist dry-run results per item**

After a local run, write `completed`, `skipped` or `failed` only for targets
present in that run. Store one concise error string for failed targets. Do not
change `apply_status` or `helpers_status` from a dry-run.

- [ ] **Step 4: Implement the table UI**

Add `Все задачи` beside `Проверка`. Columns: `Задача`, `Условие`, `Решение`,
`Ответ`, `Картинки`, `Dry-run`, `Apply`, `Helpers`, `Итог`. Add filters `Все`,
`Готово`, `Пропущено`, `Ошибки`. Clicking a row selects that problem for the
existing preview panel; it does not create a per-task comment.

- [ ] **Step 5: Run tests and build**

Run: `.venv/bin/pytest -q tests/test_group_inventory_store.py tests/dashboard`

Run: `cd dashboard && npm test -- --run && npm run build`

- [ ] **Step 6: Commit**

```bash
git add src/solution_runner/group_inventory_store.py src/solution_runner/dashboard dashboard/src tests
git commit -m "feat: show per-task group progress"
```

---

### Task 6: Existing-card migration and end-to-end verification

**Files:**
- Modify: `src/solution_runner/dashboard/store.py`
- Modify: `src/solution_runner/dashboard/server.py`
- Test: `tests/dashboard/test_store.py`
- Test: `tests/dashboard/test_server.py`
- Modify: `README.md`

**Interfaces:**
- Consumes: initialization API, local launcher path and per-task state from Tasks 1–5.
- Produces: safe migration state for all existing cards without background MCP load.

- [ ] **Step 1: Write the migration test**

Seed an existing `done` card and an existing unprocessed card. On schema upgrade,
assert the done card retains its column, both inventories are `pending`, and no
MCP request occurs. Explicit Initialize changes only the selected card.

- [ ] **Step 2: Implement lazy migration**

Do not initialize 318 groups at server startup. Existing cards stay in their
current columns and display `Индекс не создан`; Initialize is explicit. New
cards follow the automatic `Инициализация` flow from Task 3.

- [ ] **Step 3: Document the operator flow**

README must show: add group → Initialize → inspect inventory → register handler
→ dry-run from SQLite. Document `--inventory-db` as the transition path and say
that MCP inventory fallback will be removed only after all required groups have
ready local indexes.

- [ ] **Step 4: Run complete verification**

Run: `.venv/bin/pytest -q`

Run: `cd dashboard && npm test -- --run && npm run build`

Run: `git diff --check`

- [ ] **Step 5: Commit**

```bash
git add README.md src/solution_runner/dashboard tests/dashboard
git commit -m "docs: finish local inventory rollout"
```
