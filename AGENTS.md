# SolutionRuner repository rules

## One shared checkout

- Work only in the saved project checkout: `/Users/a1/projects/SolutionRuner`.
- Do not create or use Codex worktrees for this repository.
- When creating a Codex task for this project, select the saved project directly and use the local environment, not a worktree environment.
- Do not create temporary implementation branches for routine runner work. Keep changes in the shared checkout so the user does not have to merge or clean up task worktrees.
- Preserve changes made by other tasks. Before editing, inspect the current working tree and avoid overwriting unrelated or unfinished work.

## Accumulating project experience

- Treat this repository as the canonical home for runners, launchers, converters, fixtures, operational commands, and lessons learned. Do not leave the only useful copy in TeacherHelper, svg_parseer, ignored files, or a task transcript.
- Before implementing a runner, read `docs/project-experience.md` and the relevant package README files.
- After learning a reusable rule, edge case, MCP contract, deterministic validation rule, or safe operator procedure, update `docs/project-experience.md` in the same task.
- Keep group-specific behavior in explicit profiles, strategies, fixtures, and tests. Reuse the common launcher, MCP gateway, manifests/resume machinery, and converter infrastructure instead of copying them.
- Treat the task condition plus the registered deterministic rule as the source of truth. Existing answers, solutions, Helpers state, and task assets are repair targets, not authoritative validation inputs.
- When a stored answer or solution is missing, malformed, non-numeric, or disagrees with the deterministic computation, rewrite it to the computed canonical value. This mismatch must not block the task and must not block other tasks in the group.
- Apply fail-closed behavior per task: if one condition is unsupported, ambiguous, or cannot be computed deterministically, perform no writes for that task, record a clear failure, and continue processing independent tasks.
- Do not add whole-group preflight checks that reject a run because individual tasks contain repairable content errors. Stop the whole run only for a group-wide safety failure such as wrong catalog/group scope, invalid configuration, unavailable authorization, corrupt frozen inventory, or a shared invariant that makes every write unsafe.
- Record commands that can change MCP or production data, but never run them unless the user explicitly authorizes the run. Keep `--apply` commands clearly separated from safe local verification commands.
- Before running tests, tell the user the exact command that will be executed.
