# Grid-polygon solution strategies

[Project](../../../../../README.md) →
[Grid-polygon pipeline](../README.md) → **Strategies**

This directory owns pure, reusable geometry-to-solution behavior. Strategies
consume one frozen prepared figure plus immutable `GroupProfile` data and
produce verified analysis, solution HTML, answer HTML, and (when required) a
solution SVG overlay.

`bounding_rectangle_triangle.py` owns the shared rectangle-complement engine;
`bounding_rectangle_quadrilateral.py` reuses it for ordered convex and concave
four-vertex figures without imposing trapezoid-only parallel-side rules.
Axis-monotone concave figures keep one outer rectangle; a non-monotone figure
falls back to an outer triangle minus its triangular notch. The
`quadrilateral-pick` profile renders the construction as the first solution and
an independently enumerated Pick formula as the second solution;
`quadrilateral-pick-first` keeps the same verified methods but follows a parent
whose Pick method comes first. Its
`rhombus-two-methods` profile remains the specialized diagonal alternative for
the audited rhombus group.

`parallelogram_three_methods.py` validates an axis-based parallelogram once,
then reuses the quadrilateral complement and lattice-node engines to present
base-height, bounding-rectangle, and Pick solutions with separate diagrams.

`grid_cell_count.py` handles variable-vertex figures made from whole grid cells.
It enumerates covered unit-cell centers, verifies the count against exact
shoelace area, and reproduces the concise prototype wording without generating
an additional solution diagram.

`annulus_area.py` consumes `PreparedGridRing`, verifies both radius squares
against center-to-lattice-point distances, and presents the exact quotient
`S / pi = R1^2 - R2^2`. Its generated diagram preserves the condition ring and
adds only two labelled radius segments.
`annulus_from_known_area.py` handles rings where a task states the inner- or
outer-circle area. It uses task-local condition detection and the exact parsed
radius ratio, supports concentric and offset nested circles, and produces no
extra solution diagram.

Every multi-method strategy returns explicit solution-section wrappers. The
runtime inserts the one generated SVG at the start of the first section only;
later text-only methods never reference that asset.

Strategies do not know group IDs, call MCP, invoke converters, discover files,
sleep, batch work, or emit progress. Transport and orchestration live in the
parent package.
