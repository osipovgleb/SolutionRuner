"""SQLite schema for the dashboard state store."""

SCHEMA = """
CREATE TABLE IF NOT EXISTS removed_groups (
    group_key TEXT PRIMARY KEY
);
CREATE TABLE IF NOT EXISTS groups (
    group_key TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    path TEXT NOT NULL,
    source TEXT NOT NULL,
    source_id TEXT NOT NULL,
    registered INTEGER NOT NULL,
    legacy INTEGER NOT NULL,
    workflow TEXT,
    handler TEXT,
    total INTEGER NOT NULL DEFAULT 0,
    transformed INTEGER NOT NULL DEFAULT 0,
    helpers INTEGER NOT NULL DEFAULT 0,
    errors INTEGER NOT NULL DEFAULT 0,
    blocked INTEGER NOT NULL DEFAULT 0,
    latest_run TEXT,
    run_status TEXT,
    system_column TEXT NOT NULL,
    manual_column TEXT,
    manual_source TEXT,
    revision_requested INTEGER NOT NULL DEFAULT 0,
    existing_solution_policy TEXT NOT NULL DEFAULT 'preserve',
    condition_image_policy TEXT NOT NULL DEFAULT 'auto',
    solution_image_policy TEXT NOT NULL DEFAULT 'auto',
    verify_answers INTEGER NOT NULL DEFAULT 1,
    verify_helpers INTEGER NOT NULL DEFAULT 1,
    agent_sample_size INTEGER NOT NULL DEFAULT 1,
    task_title TEXT,
    task_url TEXT,
    codex_thread_id TEXT,
    codex_archived INTEGER NOT NULL DEFAULT 0,
    full_dry_run_status TEXT,
    agent_status TEXT,
    agent_summary TEXT,
    source_navigation TEXT,
    synced_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_key TEXT NOT NULL REFERENCES groups(group_key) ON DELETE CASCADE,
    problem_id TEXT,
    author_type TEXT NOT NULL DEFAULT 'user',
    body TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""
