# Codex registration implementation plan

1. Extend the SQLite group record with a stable Codex thread ID and a persisted
   full-group dry-run readiness flag.
2. Add a small standard-library Codex integration that lists project tasks,
   creates a Terra/medium task, or queues the registration/feedback prompt to an
   existing task.
3. Add registration API endpoints and forward review/problem comments to the
   linked task.
4. Make full-group dry-runs set `issues`/`review` and make group Apply require
   the persisted successful full-group result.
5. Reorder the Kanban columns and replace the manual link editor with a task
   picker and automatic-create option.
6. Verify backend tests, frontend tests, production build, and the safe UI path
   without creating a real task or writing through MCP.
7. Commit the dashboard-related changes, push them, and move this Codex task out
   of the `Эксперименты` sidebar section.
