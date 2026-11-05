"""Verify isometries, exact source reuse, remapped scenes and strict asset identity."""

import hashlib
import itertools
import xml.etree.ElementTree as ET
from copy import deepcopy

import pytest
from bs4 import BeautifulSoup
from midpoint_source_cases import replay, section
from prism_metric_oracle import points
from prism_metric_source_cases import CASES, GROUPS, generated, plan, read

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.solids import regular_prism_geometry as g
from solution_runner.pipelines.solids.prism_metric_figures import (
    KEY,
    choice,
    mapped_scene,
)
from solution_runner.pipelines.solids.prism_sources import DATA, source_bytes


@pytest.mark.parametrize("body", ["cube", "square", "triangle", "hexagon"])
def test_every_body_isometry_preserves_all_pairwise_lengths(body):
    m = read(next(c for c in CASES if read(c).body == body))
    p = points(m)
    mappings = list(g.isometries(body))
    assert (
        len(mappings) == {"cube": 48, "square": 16, "triangle": 12, "hexagon": 24}[body]
    )
    for mapping in mappings:
        assert set(mapping) == set(mapping.values()) == set(p)
        for a, b in itertools.combinations(p, 2):
            u = p[b] - p[a]
            v = p[mapping[b]] - p[mapping[a]]
            assert (u.dot(u) - v.dot(v)).simplify() == 0


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_solution_scene_is_exact_native_or_isometric_and_replay_retains_roles(case):
    ctx = deepcopy(case["context"])
    m = read(case)
    handler = get_handler(GROUPS[case["group"]]["rule"])
    drawings = handler.diagram_specs(ctx)
    assets = {a["asset_key"]: a for a in ctx["normalized_content"]["assets"]}
    owners = {
        k: s["key"]
        for s in ctx["normalized_content"]["sections"]
        for k in s["asset_keys"]
    }
    source, drawing = choice(m, assets, owners)
    if drawing:
        assert drawings == (drawing,)
        assert (
            hashlib.sha256(drawing["svg_text"].encode()).hexdigest()
            == drawing["sha256"]
        )
        root = ET.fromstring(drawing["svg_text"])
        assert root.tag.endswith("svg") and "<image" not in drawing["svg_text"]
        template = next(t for t in DATA["metric_templates"] if t["source"] == source)
        mapping = next(
            t
            for t in g.isometries(m.body)
            if mapped_scene(m, t) == tuple(template["scene"])
        )
        inverse = {v: k for k, v in mapping.items()}
        labels = {n.get("id"): n for n in root if n.get("id", "").startswith("label-")}
        assert set(labels) == {"label-" + inverse.get(n, n) for n in template["names"]}
    else:
        assert drawings == ()
        assert any(
            (s["source"], s["body"], s["kind"], s["method"], tuple(s["scene"]))
            == (source, m.body, m.kind, m.method, m.scene)
            for s in DATA["metric_scenes"]
        )
        assert source_bytes(source)
    replay(ctx, plan(case, ctx).transformations)
    assert len(section(ctx, "solution")["asset_keys"]) == 1
    assert (
        len(
            BeautifulSoup(section(ctx, "solution")["html"], "html.parser").find_all(
                "img"
            )
        )
        == 1
    )
    assert plan(case, ctx).transformations == ()


@pytest.mark.parametrize("field", ["asset_key", "sha256", "source_asset_id", "url"])
def test_generated_asset_identity_is_checked(field):
    case = next(c for c in CASES if c["task"] == "273055")
    args = list(generated(case, case["context"]))
    args[0][field] = "foreign"
    with pytest.raises(ContentPlanError):
        plan(case, generated_solution_assets=tuple(args))


@pytest.mark.parametrize("task", ["245365", "316554", "316558", "318475"])
def test_foreign_native_diagram_rejected(task):
    case = next(c for c in CASES if c["task"] == task)
    ctx = deepcopy(case["context"])
    a = ctx["normalized_content"]["assets"][0]
    a["asset_id"] = "foreign"
    a["url"] = "/assets/foreign"
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


def test_generated_key_cannot_belong_to_condition():
    case = next(c for c in CASES if c["task"] == "273055")
    ctx = deepcopy(case["context"])
    replay(ctx, plan(case, ctx).transformations)
    condition = section(ctx, "condition")
    solution = section(ctx, "solution")
    condition["html"] += str(BeautifulSoup(solution["html"], "html.parser").img)
    condition["asset_keys"].append(KEY)
    with pytest.raises(ContentPlanError):
        plan(case, ctx)
