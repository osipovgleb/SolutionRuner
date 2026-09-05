# Solution Runner

This repository is the canonical home for deterministic TeacherHelper runners,
strict source-group profiles, raster-to-SVG converters, SVG cleanup, manifests,
and their regression tests.

The former copies under `TeacherHelper/scripts/grid_polygon_pipeline` and
`svg_parseer` are migration sources only. New work must be made here after the
migration verification is complete.

## Boundaries

- `src/solution_runner/pipelines/` decides which transformations a selected
  source group requires and in which order they run.
- `src/solution_runner/converters/` transforms local image bytes. A converter
  must not independently choose a source group or silently write production
  content.
- `src/solution_runner/pipelines/grid_polygon/mcp_runtime.py` is the shared
  TeacherHelper MCP gateway for the migrated grid-polygon pipeline.
- `tests/` and its minimized fixtures are tracked.
- `var/` contains manifests, converted assets, logs, previews, caches, and
  recovery evidence and is never tracked.

## Safety contract

The group launcher defaults to a dry run. Production writes require both
`--apply` and an exact `--confirm-catalog` value. API keys are read from
`TEACHERHELPER_MCP_API_KEY` or an interactive prompt and must never be stored in
the repository or runtime manifests.

## Installation

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
npm ci
```

Tesseract.js is needed only by the temperature-chart converter. The remaining
runner and converter tests do not require Node packages unless they exercise
that OCR boundary.

## Run one group

Preview without writes:

```bash
.venv/bin/solution-runner \
  --group 27547 \
  --confirm-catalog 4073fc7b-2056-4697-b18b-38741c94d0f4
```

Apply after reviewing the frozen scope and preview:

```bash
.venv/bin/solution-runner \
  --group 27547 \
  --confirm-catalog 4073fc7b-2056-4697-b18b-38741c94d0f4 \
  --apply
```

See [the pipeline documentation](src/solution_runner/pipelines/grid_polygon/README.md),
[the runner authoring contract](docs/runner-authoring-contract.md), and
[the migration inventory](docs/migration.md) for details.
