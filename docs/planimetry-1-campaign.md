# Planimetry 1 campaign

This is the durable operating contract for completing catalog snapshot
`41bc4d03-40cd-4407-8dea-df76e3f47ea8`, category
`0255b2f6-ef48-4356-8edf-aec792deb65b` (`1. Планиметрия`) without requiring
the operator to supervise every theme or group.

The campaign is deliberately split into small, restartable passes. One Codex
pass handles at most two groups, one after the other, in the shared checkout.
The pass must never run production `--apply` commands.

## Source of campaign truth

- Read the category's ordered theme identities and each theme's ordered group
  identities with `get_source_catalog_children`. These structural reads do not
  authorize reading problem content.
- A group checkpoint lives at
  `docs/campaigns/planimetry-1/GROUP.json` and conforms to
  `docs/planimetry-1-campaign-report.schema.json`.
- `ready` means the profile satisfies `docs/runner-authoring-contract.md`, its
  focused local tests pass, and a read-only group dry-run has completed with
  record-local failures isolated from later valid records.
- `blocked` means the bounded evidence is insufficient or a shared safety
  invariant prevents a deterministic implementation. Record the exact reason
  and continue with the next group.
- `needs_review` is reserved for a reproducible implementation or verification
  defect that the pass could not resolve. It does not authorize broader MCP
  research.

Missing checkpoints are work to do even when a group is already registered.
Existing profiles must therefore pass the same gates as newly authored ones.

## One group pass

1. Inspect the current working tree and preserve all unrelated changes. Work in
   `/Users/a1/projects/SolutionRuner`; do not create a branch or worktree.
2. Select the first ordered group without a terminal checkpoint. Never select
   more than two groups for one Codex pass.
3. Use the group child identity listing and compact missing-solution summary
   only to select a real repair-needed child. Read the mandatory parent and
   that one child. A second child is allowed only for an already identified
   alternative form. Do not keep sampling to discover variants.
4. Freeze the accepted grammar and record-local fail-closed boundary before any
   group batch read. After that point `get_problem_batch` is allowed only as
   runtime transport through the frozen parser. It must not broaden the rule.
5. Implement or repair the explicit profile, deterministic planner, fixtures,
   and tests. Parent HTML and assets define presentation; each child condition
   defines its own values; the deterministic rule defines the answer.
6. Announce the exact focused test command, run it, then run a read-only group
   dry-run through `.venv/bin/solution-runner`. Never include `--apply`.
7. For a `ready` checkpoint, record the parent, selected child or children,
   accepted forms, focused test command, dry-run artifact, and commit SHA when
   the pass made an isolated commit. For a non-ready checkpoint, record the
   exact blocker and the evidence already collected.
8. Continue to the second selected group even if the first one is locally
   blocked. Stop the entire pass only for catalog drift, missing authorization
   for read-only MCP, corrupt shared configuration, a held campaign lock, or a
   repository state that cannot be preserved safely.

## Terra execution policy

Terra receives this file, `AGENTS.md`, `docs/project-experience.md`, and
`docs/runner-authoring-contract.md` as its complete process contract. It must
report observed evidence, not infer readiness from a non-empty solution or a
registered profile. It must use explicit commands and checkpoint fields rather
than conversational memory.

The hourly automation processes at most two groups per run with
`gpt-5.6-terra` at high reasoning effort. Runs are serialized by convention in
the single saved-project checkout. Notifications are emitted only for failed
automation runs; ordinary `ready`, `blocked`, and `needs_review` checkpoints are
reviewed from the repository.

Production application is a separate operator campaign. Completing this
campaign prepares and dry-runs deterministic runners but does not mutate MCP
problem content or Helpers state.
