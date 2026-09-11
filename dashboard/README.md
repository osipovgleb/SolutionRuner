# Group dashboard

Local Preact dashboard based on the lightweight board interaction model of
[OpenKanban](https://github.com/clawnify/OpenKanban). A small Python API reads
registered groups and local run reports, while SQLite stores board columns,
task links, comments, and the initialized task index.

New groups move through `Инициализация` first. The backend reads their IDs,
section flags, and image metadata through MCP once and stores no problem HTML.
Dashboard dry-runs use that SQLite index through the one common launcher and
never add `--apply`; real writes remain a separate, explicit step.

After initialization, registration can reuse an existing Codex task for this
repository or create a new `gpt-5.6-terra` task with medium reasoning. A clean
full-group dry-run moves the card to review and enables Apply; a failed one moves
it to problems. Review/problem comments are forwarded to the linked Codex task
and invalidate the previous full-group approval.

```bash
npm install
npm run build
cd ..
.venv/bin/python -m solution_runner.dashboard.server
```

The built dashboard is then available at `http://127.0.0.1:8765`.
