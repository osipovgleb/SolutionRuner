# Grid-polygon pipeline tests

[Project](../../../README.md) → **Grid-polygon pipeline tests**

These tests protect the reusable square-grid polygon and annulus pipeline without network
or production writes. Minimized fixtures under `fixtures/` record hand-audited
coordinates, areas, formula fragments, and answer HTML for every active
solution strategy. They intentionally exclude complete MCP responses, signed
URLs, credentials, user identities, and full production dumps.

Later focused tests mirror package ownership: shared geometry, immutable
profiles and manifests, polygon/ring converter adaptation, pure strategies, MCP
transport, progress, solution/answer application, Helpers eligibility, and
launcher resume guards. Ring regressions cover full-circle viewport containment,
direct lattice radii, and Pythagorean construction triangles without labels.

Run the package suite with:

```bash
python3 -m pytest tests/pipelines/grid_polygon -q
```
