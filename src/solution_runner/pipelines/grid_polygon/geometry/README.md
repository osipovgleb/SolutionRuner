# Grid-polygon geometry

[Project](../../../../../README.md) →
[Grid-polygon pipeline](../README.md) → **Geometry**

This package owns side-effect-free SVG/grid interpretation and exact polygon
mathematics. `grid_polygon.py` is the only active implementation that selects
a visible SVG polygon or reconstructs a closed dark outline encoded as separate
SVG lines, extracts square-grid lines, snaps and normalizes vertices, removes
bounded intermediate edge points, and reads or writes coordinate alt metadata.

`triangle.py` and `quadrilateral.py` operate only on validated integer
coordinates. Quadrilateral geometry preserves the source polygon order, rejects
self-intersection, supports one reflex vertex, and enumerates interior and
boundary lattice nodes independently for child-facing Pick solutions.
Variable-vertex cell figures are accepted only by the explicit
`grid-cell-count` profile and must have integer axis-aligned edges.
`ring.py` recovers both circles from explicit elements or compound legacy paths,
deduplicates fill/stroke copies, verifies that the inner circle is nested, and
records concentric or per-task offset centers without forcing one group-wide
alignment.
Strategy-specific formulae must be checked against their independent shoelace
area before an answer can be produced. Geometry modules do not call MCP,
download assets, invoke the converter, select groups, or emit progress.

Run focused verification with:

```bash
python3 -m pytest \
  tests/pipelines/grid_polygon/test_grid_polygon.py \
  tests/pipelines/grid_polygon/test_triangle_geometry.py \
  tests/pipelines/grid_polygon/test_quadrilateral_geometry.py \
  tests/pipelines/grid_polygon/test_ring_geometry.py -q
```
