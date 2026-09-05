# Project experience

This file is the durable cross-task memory for SolutionRuner. Add concise, reusable findings here as runners and converters are developed.

## Repository workflow

- SolutionRuner uses one shared saved-project checkout at `/Users/a1/projects/SolutionRuner`; Codex worktrees are not used.
- Runner implementations accumulate in this repository and reuse its common launcher and infrastructure.
- Test commands are announced to the user before execution.
- MCP/production-changing commands require explicit user authorization. A requested example command containing `--apply` may be documented without being executed.

## Runner design principles

- Prefer an explicit group profile plus a pure deterministic strategy over a separate launcher.
- Validate all supported input forms explicitly and fail closed on unknown or ambiguous cases.
- Derive the canonical answer from the condition and deterministic rule. Existing answer/solution content is a repair target; missing, damaged, or contradictory stored content must be replaced rather than treated as a blocker.
- Isolate unsupported or ambiguous conditions per task: write nothing for that task, report it, and continue unrelated tasks. Reserve whole-run failure for shared scope, configuration, authorization, inventory, or safety failures.
- Cover reusable behavior with local fixtures and fake-MCP tests.

## Group-specific findings

Add dated entries here when a group investigation produces rules that may help future runners.

### 2026-09-05 — group 27591: included-angle area and answer integrity

- Source snapshot `41bc4d03-40cd-4407-8dea-df76e3f47ea8`, group
  `cba0bfd4-8e64-4d51-812e-0049e9e86e9b`: parent `27591` proves `S=ab/4`
  for an included 30° angle. Text `30°` and an empty inline-LaTeX
  `30^{\circ}` span are both observed; restore formulas at their text position
  and match the complete condition, not a substring of givens.
- A shared SVG may be schematic rather than metric. The parent's ABC diagram
  has no measurements or marked angle; do not infer geometry from its pixels.
  Reuse an already normalized SVG SourceAsset without a redundant converter or
  upload. Asset `4e20eaee-c328-4838-a749-0e6c1343eb60` belongs in condition only.
- Materialized answers are not automatically trustworthy. Among 28 observed
  tasks are wrong numeric answers (55261: stored 400, computed 200) and damaged
  answers. The computed canonical answer must replace such stored values; these
  repair targets must not block the task or the rest of the group.
- Fail closed at the record boundary. An unsupported or ambiguous condition
  receives no writes and a clear failure result, while independent records keep
  running. Group 27591 must not use a whole-manifest answer-integrity preflight.
- Contract, safe local test command, and the unexecuted production operator
  command are tracked in
  `src/solution_runner/pipelines/grid_polygon/general_triangle_pipeline/README.md`.

### 2026-09-05 — single-task apply 55259

- `get_problem_transformation_context` includes canonical
  `data-transformation-target-id="asset:image_1"` in image HTML, unlike the
  public `get_problem` read. Accept that exact target only; fixture coverage
  must include the transformation-context shape used by the gateway.
- Transformation context does not supply `source_problem_id`. Verify the
  frozen source number using the group's catalog membership and compare the
  returned internal `problem_id` separately.
- Exact single-task selection uses `--only-source-problem-id 55259`. An
  authorized apply succeeded for internal problem
  `96c14575-35bf-424c-8893-53c441b54889`: solution added, answer 32 verified,
  parent SVG attached to condition, Helpers ready. Readback confirmed content.
- The asset add's `position: 0` is not a guarantee of image-before-text HTML:
  this server materialized the centered image after the condition paragraph.
  Always inspect materialized readback when exact placement matters.

### 2026-09-06 — representative repair targets for the next ten groups

- The representative UUID must be selected from the read-only
  `get_source_catalog_missing_solution_summary` result, not from the group
  parent. The current table in `general_triangle_pipeline/next_ten.md` uses
  one concrete missing-solution task per group and records its actual parsed
  values and expected answer.
- The selected tasks have correct numeric answers but absent solutions; they
  are useful first repair targets without changing the parent examples.

### 2026-09-05 — group 27591 repair semantics

- A nonempty solution is not automatically correct. Preserve the recognized
  parent proof with the task's computed numbers; replace unknown, malformed, or
  contradictory text with that deterministic proof. Matching numeric answers
  are preserved, while absent or damaged answers are added/rewritten.
- Shared manifest validation is structural: pinned catalog/group/asset,
  unique records, record status/shape, and source-catalog membership. It does
  not validate repairable parent or child answers before dispatch.
- Frozen-input or condition drift at apply/resume is a record-local failure:
  no write to that record, an explicit result, and continued independent work.
  Fresh preparation is required for outstanding stale repairs. Completed
  records remain idempotent. No production run accompanied this revision.

### 2026-09-06 — targeted single-problem initialization

- `--only-problem-id` and `--only-source-problem-id` are execution scope, not a
  filter to apply after full inventory. Validate exact membership from the
  group's ordered child identities, then read pipeline state/context/assets
  only for selected tasks.
- Content-rule targeted runs also retain the canonical parent target because it
  supplies the shared audited asset/proof contract. They must not classify the
  remaining children or request the group image/missing-solution audits.
- Use `TARGET SELECTION` progress events for this path so operators can tell it
  apart from a full group `INVENTORY` run.

### 2026-09-06 — incident review: static parent solutions

- A parent solution is a syntax and layout template, not child output. Copying
  its HTML unchanged can produce plausible-looking but mathematically wrong
  solutions and false `ALREADY COMPLETE` results.
- Prove adaptation with at least two children whose condition values differ.
  Assert the parsed values, every substituted inline-LaTeX expression, the
  computed answer, paragraph placement, parent asset behavior, and fresh
  readback separately.
- Use a concrete child from the repair-needed inventory for acceptance. A
  parent UUID proves only the reference template and must not stand in for the
  task the operator intends to repair.
- Operational instructions are part of correctness: use the repository-local
  `.venv/bin/solution-runner`, retain the exact task selector, distinguish a
  targeted run from full inventory, and never claim a visible terminal run
  that was not actually executed there.
