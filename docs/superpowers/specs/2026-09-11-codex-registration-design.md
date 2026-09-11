# Codex registration workflow

## Goal

Make the dashboard's Kanban reflect the real lifecycle of a registered group and
connect each group to a real Codex task instead of a manually entered label.

## Workflow

The columns are ordered as follows:

1. `initialization` — build the SQLite inventory.
2. `queue` — wait for Codex registration.
3. `work` — Codex is adapting or creating the runner.
4. `issues` — a full deterministic dry-run found problems.
5. `review` — a full deterministic dry-run is clean, or Codex explicitly asks
   for a human decision.
6. `done` — Apply and Helpers have completed for the whole group.

Registration is an explicit action in `queue`. The user can select any existing
Codex task whose working directory is SolutionRunner. If no task is selected,
the backend creates one with `gpt-5.6-terra` and medium reasoning. Several groups
may share one task. The stable Codex thread ID is stored in SQLite.

The registration prompt tells Codex to use the SQLite inventory, inspect the
parent, nearby groups, and existing runners, reuse or minimally adapt a runner
when possible, register the group, and technically validate the parent plus one
child without Apply. It must not run the dashboard's full-group review dry-run;
that remains a user action.

## Review and feedback

Only a successful full-group dry-run enables group Apply. A full-group failure
moves the card to `issues`; a success moves it to `review`. Targeted, parent, and
random dry-runs never change the Kanban column.

Comments submitted from `issues` or `review` are saved locally, sent to the
linked Codex task, and move the card back to `work` with `revision_requested`.
Codex may manually put a card in `review` when it needs a decision, but this does
not enable Apply without a successful full-group dry-run.

Rejected tasks remain excluded from inventory, display, analysis, and runs.
