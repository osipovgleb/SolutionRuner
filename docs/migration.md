# Migration inventory

Solution Runner replaces two unversioned or ignored source locations with one
tracked repository.

## TeacherHelper runner package

The complete ignored package
`/Users/a1/projects/TeacherHelper/scripts/grid_polygon_pipeline/` now lives at
`src/solution_runner/pipelines/grid_polygon/`.

Its complete ignored test suite and minimized fixtures moved from
`/Users/a1/projects/TeacherHelper/scripts/tests/grid_polygon_pipeline/` to
`tests/pipelines/grid_polygon/`.

The package includes the shared launcher, explicit group profiles, inventory,
frozen manifests, MCP transport/runtime, asset preparation, solution and
Helpers stages, geometry parsers, strategies, right-triangle rules,
isosceles-triangle rules, progress reporting, and recovery tooling.

## SVG and raster tools

All Python and JavaScript source files from `/Users/a1/projects/svg_parseer/`
now live under `src/solution_runner/converters/`. All root-level converter test
files moved to `tests/converters/`. The SVG template and Tesseract.js helper are
package data beside the converters that consume them.

Generated SVG/PNG directories, experiments, logs, downloaded source lists,
temporary images, caches, and `node_modules` were intentionally not copied.
They are evidence or runtime output rather than source code.

## Cutover rule

Do not delete the migration sources until the new repository passes its copied
test suites and representative dry runs. After that checkpoint, archive or
remove the old copies so this repository is the only editable source.

