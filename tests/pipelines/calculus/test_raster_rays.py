"""Read real raster rays, preserve their corner and shade the same geometry."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from xml.etree import ElementTree as ET

import pytest
from bs4 import BeautifulSoup

from solution_runner.pipelines.calculus import raster_rays, rays_runner
from solution_runner.pipelines.core.content_runtime import (
    _apply_record,
    _prepared_record,
)

ROOT = Path(__file__).parent / "fixtures/ray_rasters"
CASES = json.loads((ROOT / "contexts.json").read_text())
RULE = "calculus-raster-trapezoid-rays"
EXPECTED = {
    "323187": (2, 5, 6, False, "3"),
    "323219": (4, 4, 2, True, "12"),
    "323263": (8, 3, 4, False, "12"),
    "323273": (8, 6, 8, False, "24"),
    "323281": (8, 7, 6, True, "12"),
}


class Gateway:
    def __init__(self, context):
        self.context = deepcopy(context)
        asset = context["normalized_content"]["assets"][0]
        self.files = {
            asset["asset_id"]: (
                ROOT / (str(context["source_problem_id"]) + ".png")
            ).read_bytes()
        }
        self.uploads = 0
        self.writes = 0

    def get_problem_context(self, problem_id):
        return deepcopy(self.context)

    def download_condition_asset(self, target):
        content = self.context["normalized_content"]
        condition = next(s for s in content["sections"] if s["key"] == "condition")
        asset = next(
            a for a in content["assets"] if a["asset_key"] in condition["asset_keys"]
        )
        data = self.files[asset["asset_id"]]
        return SimpleNamespace(
            data=data,
            content_type="image/png"
            if data.startswith(raster_rays.PNG)
            else "image/svg+xml",
        )

    def get_source_asset(self, asset_id):
        return {
            "source_asset": {"sha256": hashlib.sha256(self.files[asset_id]).hexdigest()}
        }

    def get_problem_asset_target_context(self, *args):
        return {}

    def upload_solution_asset(self, *, source_problem_id, svg_bytes, sha256):
        self.uploads += 1
        asset_id = "uploaded-" + sha256[:16]
        self.files[asset_id] = svg_bytes
        return {
            "source_asset_id": asset_id,
            "url": "/assets/" + asset_id,
            "sha256": sha256,
        }

    def apply_problem_transformations(self, problem_id, transformations):
        self.writes += 1
        content = self.context["normalized_content"]
        for change in transformations:
            target = change["transformation_target_id"]
            value = deepcopy(change["value"])
            if target.startswith("asset:"):
                key = target.removeprefix("asset:")
                content["assets"][:] = [
                    a for a in content["assets"] if a["asset_key"] != key
                ]
                content["assets"].append(value)
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
                section.update(value)
        return {}


@pytest.mark.parametrize("context", CASES, ids=lambda c: str(c["source_problem_id"]))
def test_normal_prepare_apply_readback_and_shaded_copy(context):
    gateway = Gateway(context)
    original = deepcopy(context)
    q, _, _ = rays_runner._read(context)
    data = next(iter(gateway.files.values()))
    model = raster_rays.recover(data, q.lower, q.upper)
    expected = EXPECTED[str(context["source_problem_id"])]
    assert (model["height"], model["join"], model["zero"], model["rising"]) == expected[
        :4
    ]
    record = _prepared_record(gateway, context, None, RULE)
    assert record["status"] == "prepared", record
    assert record["expected_answer"] == expected[4]
    assert len(record["generated_diagrams"]) == 2
    assert gateway.uploads == gateway.writes == 0 and gateway.context == original
    condition, shaded = [
        ET.fromstring(s["svg_text"]) for s in record["generated_diagrams"]
    ]
    ns = raster_rays.NS
    assert condition.find(ns + 'polygon[@id="integral-area"]') is None
    assert shaded.find(ns + 'polygon[@id="integral-area"]') is not None
    condition.remove(condition.find(ns + "metadata"))
    shaded.remove(shaded.find(ns + "metadata"))
    shaded.remove(shaded.find(ns + 'polygon[@id="integral-area"]'))
    assert ET.tostring(condition) == ET.tostring(shaded)
    assert [n.attrib for n in condition.iter() if n.get("data-ray-segment")] == [
        n.attrib for n in shaded.iter() if n.get("data-ray-segment")
    ]
    assert (
        float(condition.get("width")) % 20 == 0
        and float(condition.get("height")) % 20 == 0
    )
    result = _apply_record(gateway, record, None, RULE)
    assert result["status"] == "applied", result
    assert gateway.uploads == 2 and gateway.writes == 1
    solution = next(
        s
        for s in gateway.context["normalized_content"]["sections"]
        if s["key"] == "solution"
    )
    assert solution["asset_keys"] == ["integral_shading"]
    assert len(BeautifulSoup(solution["html"], "html.parser").find_all("img")) == 1
    again = _prepared_record(gateway, gateway.context, None, RULE)
    assert again["status"] == "prepared" and again["transformations"] == [], again
    result = _apply_record(gateway, again, None, RULE)
    assert result["status"] == "already_complete", result
    assert gateway.uploads == 2 and gateway.writes == 1


def test_future_problem_and_asset_ids_need_no_transcription_entry():
    context = deepcopy(CASES[0])
    gateway = Gateway(context)
    data = next(iter(gateway.files.values()))
    context.update(problem_id="new-problem", source_problem_id="new-task")
    asset = context["normalized_content"]["assets"][0]
    old = asset["asset_id"]
    asset["asset_id"] = "new-raster"
    asset["url"] = "/assets/new-raster"
    condition = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    condition["html"] = condition["html"].replace(old, "new-raster")
    assert len(rays_runner.diagram_specs(context, condition_asset_bytes=data)) == 2


def test_incompatible_bounds_and_blank_images_are_refused():
    import io

    from PIL import Image

    q, _, _ = rays_runner._read(CASES[0])
    data = (ROOT / "323187.png").read_bytes()
    with pytest.raises(ValueError, match="bounds disagree"):
        raster_rays.recover(data, q.lower, q.upper + 1)
    stream = io.BytesIO()
    Image.new("RGB", (300, 300), "white").save(stream, format="PNG")
    with pytest.raises(ValueError):
        raster_rays.recover(stream.getvalue(), q.lower, q.upper)


def test_a_future_raster_integral_uses_the_same_transformer_and_shaded_copy():
    context = deepcopy(CASES[0])
    condition = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    image = BeautifulSoup(condition["html"], "html.parser").find("img")
    condition["html"] = (
        r'<p>На рисунке изображён график функции <span data-inline-latex="y=f(x)"></span>. '
        r"Пользуясь рисунком, вычислите определённый интеграл "
        r'<span data-inline-latex="\int_{4}^{6} f(x)\,dx"></span>.</p>' + str(image)
    )
    gateway = Gateway(context)
    record = _prepared_record(gateway, context, None, RULE)
    assert record["status"] == "prepared", record
    assert record["expected_answer"] == "3"
    assert len(record["generated_diagrams"]) == 2
    solution = next(
        t["value"]["html"]
        for t in record["transformations"]
        if t["transformation_target_id"].startswith("section:solution")
    )
    assert "Это трапеция с основаниями" in solution
    assert r"S_{\mathrm{тр}}" not in solution and r"S_{\mathrm{пр}}" not in solution
    assert 'data-asset-key="integral_shading"' in solution
