# General-triangle content rules

Group `27591` uses the existing `solution-runner` launcher, MCP gateway,
content-rule frozen manifests, readback/resume, and Helpers stage. There is no
second CLI. The pure planner has no network or file operations.

## Audited reference (2026-09-05, read-only MCP)

- Snapshot: `41bc4d03-40cd-4407-8dea-df76e3f47ea8`.
- Path: `1. Планиметрия / Треугольники общего вида / Группа 27591`.
- Source group: `cba0bfd4-8e64-4d51-812e-0049e9e86e9b` (index 0).
- Theme: `ade013e0-059b-4b5e-bdb4-b4d701c2ca76` (index 2).
- Parent problem: `79ac61c1-1e29-4010-b3a5-22a628bb98d6`, source `27591`.
- Condition: two sides 8 and 12, included angle 30°, requested area; answer 24.
- Proof: half the product of the two side lengths and sine of their included
  angle; substitute `sin 30° = 1/2`, giving `S = ab/4`.
- Asset `4e20eaee-c328-4838-a749-0e6c1343eb60` is already SVG, a schematic ABC
  triangle without numerical measurements or marked angles. Its apparent angles
  are not data. `image_1` occurs first in condition, with no solution assets.
  Reuse the stored SourceAsset; no raster conversion, OCR, upload, or generated
  replacement is needed. The shared converter infrastructure remains unchanged.

## Explicit accepted input

Schema-v3 Normalized with a unique canonical condition and optional unique
answer/solution sections. The complete normalized condition must be:

`Найдите площадь треугольника, две стороны которого равны A и B, а угол между ними равен 30°.`

`A` and `B` are positive integers of at most six digits without leading zeros.
Only whitespace normalization, soft-hyphen removal, and the audited empty
`<span data-inline-latex="30^{\circ}"></span>` angle spelling are accepted.
Text uses `p`, `span`, or `center` wrappers with explicitly allowed attributes.
Side fractions, side decimals, alternate angles, extra clauses, hidden markup,
and formula/fallback conflicts are rejected rather than guessed.

Compute `A*B/4` with exact rational arithmetic. The condition and registered
rule are authoritative. Missing, empty, malformed, nonnumeric, or incorrect
stored answers produce an add/rewrite to the canonical decimal answer. A correct
numeric answer (decimal dot or comma) is preserved. Unknown or contradictory
solution text is replaced with the parent's proof using this task's own numbers;
the recognized correct proof is preserved, including source spacing and soft
hyphens. Thus nonempty solution text alone is not a reason to skip a repair.
Attach the audited asset only when absent. Unrecognized image layouts remain a
per-task unsupported layout error, never a whole-group content blocker.

Before batch dispatch, shared validation checks catalog/group scope, the pinned
shared asset identity, manifest record structure, unique identities, and catalog
membership. It does not read or validate all tasks' answers or the parent's
repairable content. A prepared record's condition and frozen input are rechecked
locally immediately before writing; post-write readback must yield no repairs.
Resume uses the same per-record checks and skips already completed content.
Stale outstanding repairs require fresh preparation for that task and do not
stop independent records.

An unsupported or ambiguous condition receives zero writes and a clear blocked
result. Independent records continue, including when an invalid task comes first.
Whole-run failure is reserved for shared scope/configuration/inventory safety
errors. Existing wrong/nonnumeric answers are ordinary repair targets: the audit
found, for example, source `55261` with sides 40 and 20 and stored answer 400;
its repair writes 200. The shared ready-status eligibility and explicit operator
selection still determine inventory.

## Local verification

```bash
python3 -m pytest tests/pipelines/grid_polygon/test_general_triangle_planner.py -q
```

The fixtures contain the real parent, one valid missing-solution child, and one
incorrect-answer child. Tests use fake MCP only, covering answer/proof repairs,
per-task failure isolation, shared-safety aborts, frozen-input drift, idempotent
readback, and resume. No live runner or MCP writes were used for this semantic
revision.

## Operator command (changes production; not executed)

```bash
solution-runner \
  --group 27591 \
  --confirm-catalog 41bc4d03-40cd-4407-8dea-df76e3f47ea8 \
  --max-workers 1 \
  --batch-size 1 \
  --apply
```

Resume uses the shared `--resume-solutions RUN_DIR` option with the same group
and catalog gates; it retains shared-scope validation and per-task frozen-plan/readback checks.
