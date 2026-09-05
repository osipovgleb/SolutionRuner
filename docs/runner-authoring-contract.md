# Runner authoring contract

This contract is mandatory for every new or changed group profile. It captures
the failure modes found while building and operating the first general-triangle
runners. A task is not complete merely because a planner returns output or one
fixture passes.

## Research scope

The default and maximum unapproved content sample is:

- the mandatory parent problem; and
- one explicitly selected non-parent child that currently needs repair.

One additional child may be read only when a known alternative serialization or
condition form must be represented. Researching more than two children requires
explicit user authorization before the reads occur.

It is acceptable to read the group's child identity listing and a compact
missing-solution summary solely to select the representative child IDs. It is
not acceptable to batch-fetch or enumerate the conditions, answers, solutions,
transformation contexts, pipeline states, or assets of the whole group during
profile design. Do not use `get_problem_batch` over the group and do not keep
sampling children to gain confidence.

The parent and one or two selected children define the explicit accepted form.
Anything not proven by that sample is handled by record-local fail-closed at
runtime. Fail-closed exists precisely so exhaustive group research is not
required.

## Sources of truth

Use each input for exactly one purpose:

- The child condition supplies the concrete values to parse and compute.
- The registered deterministic rule defines the mathematics and canonical
  answer.
- The parent condition, solution, and asset supply the approved presentation:
  wording, paragraph structure, inline-LaTeX structure, and diagram identity.
- Existing child answer, solution, asset placement, and Helpers state are
  repair targets. They are never mathematical authority.

Do not copy a parent's solution as static HTML. Parse the parent once into an
explicit template, parse every child independently, map semantic variables,
and substitute all affected expressions. Preserve the parent's surrounding
prose and LaTeX structure exactly unless the profile documents an intentional
paragraph or punctuation change.

## Per-task algorithm

For every selected child:

1. Freshly read its transformation context and verify catalog membership and
   internal/source identity.
2. Parse the complete condition using the profile's explicit accepted forms.
   Do not infer missing values from the picture or accept a substring match.
3. Map child values to parent variables and compute with exact arithmetic.
4. Render a solution from the parent template with the child's values. Every
   number and derived expression in inline LaTeX must be accounted for; an
   unexplained parent literal is a profile error.
5. Derive the canonical answer from the computation. Replace missing,
   malformed, nonnumeric, or contradictory stored answers and solutions.
6. Reuse the exact audited parent asset when required and absent. Preserve an
   already matching asset; reject ambiguous/foreign layouts for that task and
   never duplicate an image.
7. Apply only the frozen transformations for that task, then freshly read back
   condition, solution, answer, assets, and Helpers state. Report success only
   when the recomputed plan is empty.

Unsupported or ambiguous input receives zero writes and a clear record-local
failure. Independent records continue. Abort the whole run only for shared
scope, catalog, authorization, frozen-inventory, or configuration corruption.

## Exact-problem operation

`--only-source-problem-id` and `--only-problem-id` define execution scope; they
are not post-inventory filters. Validate membership from the group's child
identities, then read/classify only selected tasks plus the canonical parent
needed by a content rule. Log `TARGET SELECTION`, not `INVENTORY`.

Commands shown to an operator must work from the repository root. Prefer the
installed local executable:

```bash
.venv/bin/solution-runner \
  --group GROUP \
  --confirm-catalog CATALOG_SNAPSHOT_ID \
  --only-source-problem-id SOURCE_TASK_NUMBER \
  --max-workers 1 \
  --batch-size 1 \
  --apply
```

Do not omit an exact selector when the user asked for one task. Do not execute
`--apply` until explicitly authorized. State the exact command before running
tests or a production command, and report the actual execution surface and
result; do not imply that a side terminal was used when it was not.

## Definition of done

A group profile is ready only when all of the following are demonstrated:

- Read-only audit records the exact parent problem, parent solution HTML,
  parent asset, accepted condition forms, and values to parse.
- A table or profile document names every parsed input, the deterministic
  formula, derived answer, and a real non-parent child that currently needs
  repair.
- Tests cover the parent and at least one selected child with different values
  so static parent copying cannot pass. A second MCP child is used only for a
  known alternative input form; additional parser cases use local synthetic
  fixtures rather than wider production research.
- Tests assert adapted inline LaTeX and paragraph placement, not only the final
  answer.
- Tests cover correct, missing, malformed, and incorrect stored answers and
  solutions.
- Tests cover missing parent asset, already-correct asset, and rejection of
  foreign or duplicate assets.
- Tests prove one unsupported task makes no writes while later valid tasks
  continue.
- Tests prove a fresh run without `--resume-solutions` recomputes desired state;
  `ALREADY COMPLETE` is emitted only after exact current-state comparison.
- Targeted tests prove non-selected tasks receive no state, context, or asset
  reads and the parent alone is not used as the acceptance target.
- Fake-MCP readback proves the second plan is empty after application.
- The exact test command is announced and passes. Any authorized live apply is
  performed first on the documented repair-needed child and followed by a
  fresh readback before broader operation is suggested.

## Forbidden shortcuts

- Static solution HTML shared by children whose values can differ.
- Blind text replacement without a semantic variable map.
- Treating a nonempty solution or prior manifest as proof of completeness.
- Selecting the parent as the representative repair target.
- Adding a parent image without checking whether the child already has it.
- Full-group inventory before applying an exact-problem selector.
- A bare `solution-runner` command unless the active shell environment is known
  to contain that executable.
- Declaring all groups ready from unit tests that assert only answers or only
  the parent example.
- Reading every child in a group to discover possible variants before writing a
  fail-closed parser.
- Calling `get_problem_batch` for the full group during runner design.
- Expanding beyond the parent plus two child problems without explicit user
  authorization.
