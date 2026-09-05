# Grid-polygon pipeline

[Project](../../../../README.md) → **Grid-polygon pipeline**

This tracked package owns deterministic orchestration for registered source
groups, including square-grid geometry and content-only repair rules. Group
identity and workflow selection are explicit data; shared inventory, MCP
transport, progress, solution/answer application, and Helpers application must
not be copied into group-named launchers.

## Boundaries

- [`mcp_grid_polygon_transformations.py`](../../converters/mcp_grid_polygon_transformations.py)
  is the single raster-to-SVG converter runner. This package invokes it once
  for an image stage and consumes its validated events.
- [`png_to_svg_ring_by_contrast.py`](../../converters/png_to_svg_ring_by_contrast.py)
  is the deterministic raster-annulus converter. `ring_asset_preparation.py`
  adapts its output and verifies both squared radii from the resulting SVG grid.
- Pure strategy modules receive one frozen prepared figure. They never
  download or convert a condition asset, call MCP, select a group, batch work,
  sleep, or write progress output.
- Generated manifests, assets, logs, summaries, and recovery evidence belong
  under ignored `var/grid-polygon/`.
- Durable minimized canaries and focused tests live in
  [`tests/pipelines/grid_polygon/`](../../../../tests/pipelines/grid_polygon/README.md).

## Children

The package is organized behind characterization and contract tests:

- `models.py` and `group_profiles.py` own immutable identities and profile
  data, including every audited arbitrary-quadrilateral group UUID;
- `inventory.py` concurrently reads one explicit group's ordered children,
  compact section-image audit, and missing-solution audit; it intersects those
  server-owned lists, checks pipeline state only for the narrowed candidates,
  and freezes the resulting non-rejected raster/SVG targets;
- [`geometry/`](geometry/README.md) owns canonical SVG/grid parsing and pure
  area analysis;
- [`strategies/`](strategies/README.md) owns pure diagram, explanation, and
  answer generation, including the reusable three-method parallelogram flow;
- `asset_preparation.py`, `ring_asset_preparation.py`, and `manifest.py` freeze
  prepared condition assets without forcing circles into polygon coordinates;
- `mcp_transport.py` owns JSON-RPC decoding and HTTP transport construction;
- `mcp_runtime.py`, `solution_runtime.py`, and `helpers_runtime.py` own their
  respective side-effect boundaries, while `solution_plan.py` owns pure
  solution/answer transformation construction and readback validation;
- `progress.py` owns compact console and detailed internal logging;
- `launcher.py` owns explicit-group stage ordering and resume behavior.
- [`right_triangle_pipeline/`](right_triangle_pipeline/README.md) owns the
  deterministic sine-based right-triangle content rule used by the shared
  launcher. It does not enter grid geometry or own a second CLI.
- [`general_triangle_pipeline/`](general_triangle_pipeline/README.md) owns the
  strict group-27591 included-angle area rule and its audited input contract.
- `isosceles_triangle_pipeline/` owns strict group-scoped content rules for the
  isosceles-triangle theme. Each registered group has an explicit accepted
  condition shape and requested quantity; the shared launcher remains the only
  CLI and owns MCP transport, batching, reporting, and Helpers application.

No active filename, public symbol, or strategy key is tied to a concrete group
number. Historical scripts and outputs from the source repositories are
migration evidence only and are not dependencies of this tracked package.

## Verification

Run focused tests without production access:

```bash
python3 -m pytest tests/pipelines/grid_polygon -q
```

The implementation must pass local fixture and fake-MCP tests before any
operator command is used against production.

## Operator command

After the tests pass, run one explicitly selected group. The profile selects
the reusable strategy; there is no `--after-group` and no group-named module:

```bash
solution-runner \
  --group 27547 \
  --confirm-catalog 4073fc7b-2056-4697-b18b-38741c94d0f4 \
  --max-workers 10 \
  --batch-pause-seconds 0 \
  --apply
```

`--max-workers` bounds concurrent work on independent problems and defaults to
`10` (accepted range `1..10`). Inventory reads, existing-SVG preparation,
solution/answer application, and Helpers application use the same bound. Each
problem still preserves its own write/readback order, and persisted results
remain in frozen manifest order even when console milestones complete in a
different order. Use `--max-workers 1` to force the previous sequential
behavior. The external raster-to-SVG subprocess uses the same bound as a
sliding task window: when any problem finishes, the next frozen problem starts
without waiting for the other active workers. `--batch-size 10` now controls
ordered progress checkpoints rather than a barrier between task chunks.

Omit `--apply` for a local preview. The annulus profile `245008` targets
problems whose solution is empty or was generated by this pipeline, leaving
reference solutions untouched. A repeated ordinary launch resolves the original
raster from the previous asset replacement through MCP, reconverts it inside the
ring preparation module, and overwrites the generated condition and solution.
Its `annulus-area` strategy verifies `S / pi = R1^2 - R2^2`, adds a
diagram with red lattice right triangles for every Pythagorean radius, explains
each squared radius before the parent-style area calculation, and allows Helpers
only after verified solution and answer readback. Annulus SVG preparation rejects
an outer circle outside its `viewBox`, so a clipped conversion cannot be uploaded.

The content-rule profiles `27238`, `27239`, `27240`, `27242`, `27243`, `27244`,
`27617`, `27618`, `27742`, and `27753` use the same command, progress reporter,
batching, checkpoints, isolated task failures, and shared Helpers stage. Its
first task supplies only the common condition asset. Each task's own condition
selects one of two rules: known `AC` and requested `AB` divides by `cos A`;
known `AB` and requested `AC` multiplies by `cos A`. Existing substantive
solutions and already-correct answers are preserved.
Profile `27240` accepts only conditions that give `cos A` and request `AB`;
any other trigonometric input or requested side is blocked before transformations.
Profile `27242` similarly requires `tg A`, known `AC`, and requested `AB`.
Its solution starts from `tg A = BC / AC`, finds `BC`, and then finds `AB`
by the Pythagorean theorem.
Profile `27243` requires `tg A`, known `AC`, and requested `BC`. For a missing
solution it writes the single equivalence chain
`tg A = BC / AC iff BC = AC tg A = ...`; every other condition shape is
blocked before writes. A repeated run rewrites only an older solution carrying
this rule's own marker and preserves unrelated substantive solutions.
Profile `27244` uses the universal right-triangle rule. It detects whether
`A`, `B`, or `C` is the right angle, normalizes `sin`, `cos`, `tg`, or `ctg`
of either acute angle to numerator/denominator side roles, and supports every
ordered known/requested pair of distinct sides. Missing solutions contain two
or three formula rows beginning with the exact trigonometric definition.
Existing substantive solutions are preserved; their answers are recomputed,
and an already-correct task remains eligible for the shared Helpers-ready stage.
The 23 registered altitude groups in the visible source-number range
`27265–27432` use the separate fail-closed altitude rule documented in the
[right-triangle child package](right_triangle_pipeline/README.md). Their first
task supplies the common condition asset. The solver keeps the given
trigonometric function when a proportional-side and Pythagorean route reaches
the requested quantity, and derives the complementary function only when it is
actually needed. A wrong or missing materialized answer is replaced with the
exact computed result; unsupported or inconsistent conditions still fail before
content writes.
The four later elementary profiles use strict condition-specific rules:
`27617` derives area from one leg and the hypotenuse, `27618` solves the
positive quadratic root from area and a leg difference, `27742` solves the
larger acute angle from the two-angle sum and difference, and `27753` solves
the larger acute angle from an exact integer or fractional ratio. They preserve
substantive existing solutions, correct independently disproved answers, and
attach the first task's condition asset where it is absent or different.
The eleven subsequent profiles `27761`, `27765`, `27770–27775`, and
`27789–27791` cover median/bisector/altitude angle relations, the altitude to
the hypotenuse, and the two hypotenuse projections. Their shared elementary
planner accepts both visible degree text and source HTML that splits a value,
degree sign, side label, or requested segment across inline LaTeX spans. The
angle rules use exact complementary-angle identities; the length rules accept
only the audited 30°/60° conditions and exact supported `AB` forms. Unknown
line pairs, requested quantities, or numeric layouts are blocked before writes.
Groups `27766`, `642289`, and `679651` remain intentionally unregistered because
the current source groups contain only one or two tasks.

The circle groups `315122`, `315123`, and `315124` use the shared
`annulus-from-known-area` strategy for problems with a stated inner- or
outer-circle area. Preparation detects the known side and value from each
problem's condition, independently parses both actual circle centers, classifies
the ring as concentric or offset, and verifies nesting. The profile stores none
of those task-varying facts. The strategy derives the missing circle area from
the exact squared-radius ratio, writes the concise parent-style subtraction,
and leaves existing reference solutions untouched.

Continue solution/answer/Helpers from a previously verified prepared manifest
without re-running image conversion:

```bash
solution-runner \
  --group 27547 \
  --confirm-catalog 4073fc7b-2056-4697-b18b-38741c94d0f4 \
  --resume-solutions /absolute/path/to/run \
  --apply
```

To repair an exact subset without repeating group inventory, repeat the
source-problem filter in one invocation. The launcher validates every supplied
id against the frozen group before preparing assets or writing results:

```bash
solution-runner \
  --group 27547 \
  --confirm-catalog 4073fc7b-2056-4697-b18b-38741c94d0f4 \
  --only-source-problem-id 247203 \
  --only-source-problem-id 247207 \
  --apply
```

Every run writes its prepared manifest, compact/internal logs, stage results,
and summary below `var/grid-polygon/runs/`.

`solution_asset_repair.py` is the asset-only recovery boundary for generated
rectangle-method diagrams. It merges validated prepared manifests for explicit
groups, uploads only changed rectangle SVGs, and replaces only their existing
problem asset targets; it never rewrites condition, solution text, answer, or
Helpers state.
