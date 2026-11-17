"""Source-bound derivative abscissas, minimum selection, conversion and replay."""

import json
from copy import deepcopy
from pathlib import Path
from xml.etree import ElementTree as ET

import numpy as np
import pytest
from bs4 import BeautifulSoup
from graph_samples import _apply_local

from solution_runner.pipelines.calculus import derivative_abscissa_runner as runner
from solution_runner.pipelines.calculus import primitive_curves, raster_primitive
from solution_runner.pipelines.core.group_profiles import get_group_profile

FIXTURES = Path(__file__).parent / "fixtures/derivative_abscissas"
EXPECTED = {
    "40130": "5",
    "562930": "2",
    "562975": "2",
    "639945": "-3",
    "640514": "3",
    "40131": "-3",
    "514459": "-7",
    "515184": "1",
    "515185": "-6",
    "515186": "-4",
    "515187": "-3",
    "515188": "-4",
    "515189": "-2",
    "515190": "1",
    "515191": "4",
    "517193": "3",
    "517231": "-2",
    "530666": "-4",
    "515183": "5",
}


def sample(task):
    p = FIXTURES / task
    f = p.with_suffix(".png")
    f = f if f.exists() else p.with_suffix(".svg")
    return json.loads(p.with_suffix(".json").read_text()), f.read_bytes()


def prepare(context, data):
    specs = runner.diagram_specs(context, condition_asset_bytes=data)
    generated = [
        dict(
            s,
            source_asset_id="local-" + s["sha256"],
            url="/assets/local-" + s["sha256"],
        )
        for s in specs
    ]
    return runner.build_context_repair_plan(
        context, condition_asset_bytes=data, generated_solution_assets=generated
    ), specs


@pytest.mark.parametrize("group", ("40130", "40131", "515183"))
def test_registration(group):
    assert (
        get_group_profile(group).content_rule_key
        == "calculus-raster-derivative-abscissa"
    )


@pytest.mark.parametrize("task", EXPECTED)
def test_live_source_geometry_and_replay(task):
    context, data = sample(task)
    original = deepcopy(context)
    first, specs = prepare(context, data)
    assert first.answer == EXPECTED[task]
    assert context == original
    # Answers are computed from the source, including both minimum-selection cases.
    next(s for s in context["normalized_content"]["sections"] if s["key"] == "answer")[
        "html"
    ] = "<p>999999</p>"
    assert prepare(context, data)[0].answer == first.answer
    context = deepcopy(original)
    for t in first.transformations:
        if t["transformation_target_id"].startswith("asset:"):
            key = t["transformation_target_id"][6:]
            context["normalized_content"]["assets"] = [
                a
                for a in context["normalized_content"]["assets"]
                if a["asset_key"] != key
            ]
        _apply_local(context, [t])
    condition = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    assert len(BeautifulSoup(condition["html"], "html.parser").find_all("p")) == 2
    converted = next((s for s in specs if s["asset_key"] != runner.KEY), None)
    if converted:
        data = converted["svg_text"].encode()
    else:
        assert all(
            t.get("value", {}).get("asset_id")
            != next(
                a
                for a in original["normalized_content"]["assets"]
                if a["asset_key"] in condition["asset_keys"]
            )["asset_id"]
            for t in first.transformations
            if t["transformation_target_id"].startswith("asset:")
        )
    assert prepare(context, data)[0].transformations == ()


@pytest.mark.parametrize("task,extrema", [("517193", 1), ("517231", 1)])
def test_continuous_png_has_no_false_extrema_or_invented_endpoint_rings(task, extrema):
    context, data = sample(task)
    _q, _, _, _entry, _points, model, _result = runner._input(context, data)
    assert len(model["extrema"]) == extrema
    primitive_curves.verify(model)
    svg = runner._render(model)
    assert not list(ET.fromstring(svg).iter(raster_primitive.NS + "circle"))
    seg = np.asarray(model["bezier_segments"])
    a = seg[:-1, 3] - seg[:-1, 2]
    b = seg[1:, 1] - seg[1:, 0]
    a /= np.linalg.norm(a, axis=1)[:, None]
    b /= np.linalg.norm(b, axis=1)[:, None]
    assert np.max(np.linalg.norm(a - b, axis=1)) < 1e-6


def test_extra_instruction_and_nonunique_abscissa_are_rejected():
    context, data = sample("515186")
    s = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    s["html"] = s["html"].replace("наи\u00adмень\u00adшую ", "")
    with pytest.raises(ValueError, match="uniquely"):
        runner._input(context, data)
    context, data = sample("40130")
    next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )["html"] += "<p>Не учитывайте первое пересечение.</p>"
    with pytest.raises(ValueError):
        runner.diagram_specs(context, condition_asset_bytes=data)
