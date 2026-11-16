"""Dynamic PNG conversion through the normal runtime, without external writes."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest
import sympy as sp

from solution_runner.pipelines.calculus import (
    parabola_runner as runner,
)
from solution_runner.pipelines.calculus import (
    raster_parabola,
)
from solution_runner.pipelines.calculus.common import X
from solution_runner.pipelines.core.content_runtime import (
    _apply_record,
    _prepared_record,
)

ROOT = Path(__file__).parent / "fixtures/parabola_rasters"
CASES = json.loads((ROOT / "contexts.json").read_text())
RULE = "calculus-raster-parabola-area"


class Gateway:
    """Mirror source-asset replacement and authoritative readback in memory."""

    def __init__(self, context):
        self.context = deepcopy(context)
        self.data = (ROOT / (str(context["source_problem_id"]) + ".png")).read_bytes()
        self.uploads = 0
        self.writes = 0

    def get_problem_context(self, problem_id):
        assert problem_id == self.context["problem_id"]
        return deepcopy(self.context)

    def download_condition_asset(self, target):
        return SimpleNamespace(
            data=self.data,
            content_type="image/png"
            if self.data.startswith(raster_parabola.PNG)
            else "image/svg+xml",
        )

    def get_problem_asset_target_context(self, problem_id, target):
        return {}

    def get_source_asset(self, asset_id):
        return {"source_asset": {"sha256": hashlib.sha256(self.data).hexdigest()}}

    def upload_solution_asset(self, *, source_problem_id, svg_bytes, sha256):
        self.uploads += 1
        self.uploaded = svg_bytes
        return {
            "source_asset_id": "uploaded-svg",
            "url": "/assets/uploaded-svg",
            "sha256": sha256,
        }

    def apply_problem_transformations(self, problem_id, transformations):
        self.writes += 1
        content = self.context["normalized_content"]
        for change in transformations:
            target = change["transformation_target_id"]
            if target.startswith("asset:"):
                key = target.removeprefix("asset:")
                content["assets"][:] = [
                    a for a in content["assets"] if a["asset_key"] != key
                ]
                content["assets"].append(deepcopy(change["value"]))
                self.data = self.uploaded
            else:
                section = next(
                    (
                        s
                        for s in content["sections"]
                        if s.get(
                            "transformation_target_id",
                            "section:" + s.get("section_id", ""),
                        )
                        == target
                    ),
                    None,
                )
                if section is None:
                    section = {
                        "key": target.split(":")[1],
                        "transformation_target_id": target,
                    }
                    content["sections"].append(section)
                section.update(deepcopy(change["value"]))
        return {}


@pytest.mark.parametrize("context", CASES, ids=lambda c: str(c["source_problem_id"]))
def test_regular_prepare_apply_and_readback_are_idempotent(context):
    gateway = Gateway(context)
    original = deepcopy(gateway.context)
    record = _prepared_record(gateway, context, None, RULE)
    assert record["status"] == "prepared", record
    assert len(record["generated_diagrams"]) == 1
    assert gateway.context == original and gateway.uploads == gateway.writes == 0
    result = _apply_record(gateway, record, None, RULE)
    assert result["status"] == "applied", result
    assert gateway.uploads == gateway.writes == 1
    svg = gateway.data
    question, _, _ = runner._text_data(gateway.context)
    entry = raster_parabola.embedded(svg, question.primitive)
    model = runner._area(question, entry)
    assert model.result == sp.integrate(
        sp.diff(question.primitive, X), (X, model.lower, model.upper)
    )
    again = _prepared_record(gateway, gateway.context, None, RULE)
    assert again["status"] == "prepared", again
    assert again["transformations"] == again["generated_diagrams"] == []
    assert gateway.data == svg


def test_formula_and_asset_tampering_are_refused():
    context = deepcopy(CASES[0])
    gateway = Gateway(context)
    record = _prepared_record(gateway, context, None, RULE)
    gateway.context["normalized_content"]["sections"][0]["html"] += (
        "<p>Дополнительное ограничение.</p>"
    )
    result = _apply_record(gateway, record, None, RULE)
    assert result["status"] in ("blocked", "failed"), result
    assert gateway.uploads == gateway.writes == 0
    question, _, _ = runner._text_data(context)
    model = raster_parabola.recover(gateway.data, question.primitive)
    svg, _ = raster_parabola.render(model)
    with pytest.raises(ValueError):
        raster_parabola.embedded(svg.encode(), question.primitive + X)
    with pytest.raises(ValueError):
        raster_parabola.embedded(
            svg.replace("#143B8F", "#000000").encode(), question.primitive
        )


def test_future_task_does_not_need_an_id_or_checksum_entry():
    context = deepcopy(CASES[0])
    context.update(problem_id="future-problem", source_problem_id="future-task")
    condition = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    asset = context["normalized_content"]["assets"][0]
    previous = asset["asset_id"]
    asset["asset_id"] = "future-png"
    asset["url"] = "/assets/future-png"
    condition["html"] = condition["html"].replace(previous, "future-png")
    data = (ROOT / "323301.png").read_bytes()
    specs = runner.diagram_specs(context, condition_asset_bytes=data)
    assert len(specs) == 1
    assert specs[0]["svg_text"].count("<metadata") == 1


def test_svg_serialization_is_independent_of_other_converters(monkeypatch):
    from xml.etree import ElementTree as ET

    question, _, _ = runner._text_data(CASES[0])
    model = raster_parabola.recover(
        (ROOT / "323301.png").read_bytes(), question.primitive
    )
    before, _ = raster_parabola.render(model)
    monkeypatch.setattr(ET, "_namespace_map", dict(ET._namespace_map))
    ET.register_namespace("", raster_parabola.NS[1:-1])
    ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")
    after, _ = raster_parabola.render(model)
    assert after == before
    assert raster_parabola.embedded(after.encode(), question.primitive) is not None


def test_blank_graph_is_refused_before_upload():
    import io

    from PIL import Image

    data = io.BytesIO()
    Image.new("RGB", (200, 200), "white").save(data, format="PNG")
    question, _, _ = runner._text_data(CASES[0])
    with pytest.raises(ValueError, match="horizontal axis"):
        raster_parabola.recover(data.getvalue(), question.primitive)


def test_reviewed_native_svg_is_kept_byte_for_byte():
    context = json.loads((ROOT / "native-context.json").read_text())
    original = deepcopy(context)
    data = (ROOT / "323379.svg").read_bytes()
    assert runner.diagram_specs(context, condition_asset_bytes=data) == ()
    plan = runner.build_context_repair_plan(context, condition_asset_bytes=data)
    assert plan.answer == "6"
    assert context == original
    assert all(
        not t["transformation_target_id"].startswith(("asset:", "section:condition"))
        for t in plan.transformations
    )
    assert "Приведём ещё одно решение" not in plan.solution_html
    with pytest.raises(ValueError):
        runner.build_context_repair_plan(
            context, condition_asset_bytes=data.replace(b"1.25", b"1.26")
        )


def test_cap_uses_the_reviewed_template_without_grid_or_zero_on_axis():
    from xml.etree import ElementTree as ET

    model = {"coefficients": ["-3", "-54", "-240"], "span": ["-10", "-8"]}
    svg, entry = raster_parabola.render(model)
    root = ET.fromstring(svg)
    ns = raster_parabola.NS
    template = ET.parse(
        Path(raster_parabola.__file__).with_name("assets")
        / "parabola-area-template.svg"
    ).getroot()
    curve = next(n for n in root.iter(ns + "path") if n.get("stroke") == "#143B8F")
    assert {k: v for k, v in curve.attrib.items() if k != "d"} == {
        k: v for k, v in template[1].attrib.items() if k != "d"
    }
    assert not any(
        n.get("stroke", "").lower() in ("#adadad", "#adaaaa") for n in root.iter()
    )
    assert [n.text for n in root.iter(ns + "text")] == ["−10", "−8"]
    origin = root.find(ns + 'g[@id="origin-label"]')
    assert [n.get("d") for n in origin.iter(ns + "path")] == [
        n.get("d") for n in template[7].iter(ns + "path")
    ]
    assert (
        origin.get("transform") == f"translate({entry['svg_origin'][0] - 317.1145} 0)"
    )
