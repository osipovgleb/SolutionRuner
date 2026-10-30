"""Verified graphical data, event boundaries and exact unrounded intervals."""

import hashlib
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest
from bs4 import BeautifulSoup
from test_statistics_source_samples import CASES, _plan

from solution_runner.pipelines.statistics import confidence, euler
from solution_runner.pipelines.statistics.common import read


def _case(key):
    return deepcopy(next(c for c in CASES if c["task"] == key))


def _event(case, formula):
    condition = next(
        s
        for s in case["context"]["normalized_content"]["sections"]
        if s["key"] == "condition"
    )
    soup = BeautifulSoup(condition["html"], "html.parser")
    last = soup.find_all("p")[-1]
    assert last.find("img") is None
    last.clear()
    replacement = BeautifulSoup(
        '<p>Найдите вероятность события <span data-inline-latex="'
        + formula
        + '"></span>.</p>',
        "html.parser",
    )
    last.replace_with(replacement.p)
    condition["html"] = str(soup)


@pytest.mark.parametrize("key", ["509533", "509534"])
@pytest.mark.parametrize("relation", ["=", "\\gt", "\\ge", "\\lt", "\\le"])
def test_event_changes_use_the_same_verified_diagram_data(key, relation):
    case = _case(key)
    _event(case, "X" + relation + " 5")
    *_, entry, weights, indices, source = euler._input(case["context"])
    predicates = {
        "=": lambda x: x == 5,
        "\\gt": lambda x: x > 5,
        "\\ge": lambda x: x >= 5,
        "\\lt": lambda x: x < 5,
        "\\le": lambda x: x <= 5,
    }
    expected = [
        i for i, p in enumerate(entry["points"]) if predicates[relation](p["value"])
    ]
    assert indices == expected
    before = deepcopy(case["context"])
    specs = euler.diagram_specs(case["context"])
    generated = ()
    if specs:
        (spec,) = specs
        assert hashlib.sha256(spec["svg_text"].encode()).hexdigest() == spec["sha256"]
        generated = (
            {
                "asset_key": spec["asset_key"],
                "sha256": spec["sha256"],
                "source_asset_id": "local-preview",
                "url": "/assets/local-preview",
            },
        )
        root = ET.fromstring(spec["svg_text"])
        layer = next(e for e in root if e.get("data-role") == "selected-events")
        assert [int(e.get("data-event-index")) for e in layer] == expected
        assert list(ET.fromstring(source))[0].attrib == list(root)[0].attrib
    elif euler.required_assets(case["context"]):
        assert indices == next(
            o["indices"] for o in entry["overlays"] if o["indices"] == indices
        )
    plan = euler.build_context_repair_plan(
        case["context"],
        condition_asset_bytes=source,
        generated_solution_assets=generated,
    )
    assert Fraction(plan.answer.replace(",", ".")) == sum(
        (weights[i] for i in expected), Fraction(0)
    )
    assert case["context"] == before


def test_a_changed_svg_cannot_use_old_transcribed_values():
    case = _case("509533")
    source = euler._input(case["context"])[-1]
    with pytest.raises(ValueError):
        euler.build_context_repair_plan(
            case["context"], condition_asset_bytes=source + b" "
        )
    with pytest.raises(ValueError):
        euler.build_context_repair_plan(case["context"])


def test_reviewed_transcriptions_refer_to_visible_source_points():
    for asset, entry in euler._EVIDENCE.items():
        source = (
            Path(euler.__file__).with_name("assets") / (asset + ".svg")
        ).read_bytes()
        assert hashlib.sha256(source).hexdigest() == entry["sha256"]
        root = ET.fromstring(source)
        x, y, w, h = map(float, root.attrib["viewBox"].split())
        circles = [
            (float(e.get("cx")), float(e.get("cy")))
            for e in root.iter()
            if e.tag.endswith("circle")
        ]
        seen = set()
        for point in entry["points"]:
            assert (point["x"], point["y"]) in circles
            assert x < point["x"] < x + w and y < point["y"] < y + h
            assert (point["x"], point["y"]) not in seen
            seen.add((point["x"], point["y"]))
        probabilities = [
            Fraction(1, len(entry["points"]))
            if entry["uniform"]
            else Fraction(p["probability"])
            for p in entry["points"]
        ]
        assert sum(probabilities) == 1


@pytest.mark.parametrize(
    "task,exact,squared",
    [
        ("663480", r"\frac{\sqrt{3}}{3}", Fraction(1, 3)),
        ("663481", r"\frac{\sqrt{6}}{12}", Fraction(1, 24)),
    ],
)
def test_interval_length_keeps_its_exact_value_when_rounding_is_unspecified(
    task, exact, squared
):
    case = _case(task)
    plan = _plan(case, case["context"])
    text = read(case["context"])[3]
    assert "округлите" not in text
    assert plan.answer == exact
    assert "data-inline-latex" in next(
        t["value"]["html"]
        for t in plan.transformations
        if t["transformation_target_id"].startswith("section:answer")
    )
    # The interval length is 2c*sqrt(w(1-w)/n); squaring gives these rational values.
    multiplier, n = (2, 12) if task == "663480" else (1, 24)
    assert (2 * multiplier) ** 2 * Fraction(1, 4) / n == squared


def test_confidence_rounding_and_response_polarity_are_explicit():
    case = _case("663479")
    text = read(case["context"])[3]
    assert confidence.solve(text)[0] == "0,2"
    assert confidence.solve(text.replace("десятых", "сотых"))[0] == "0,21"
    with pytest.raises(ValueError):
        confidence.solve(text.replace("ответили «Да»", "ответили «Нет»"))
    assert confidence.solve(text + " В ответе удвойте результат.") is None


def test_symmetry_requires_equal_reflected_probabilities():
    case = _case("704660")
    condition = next(
        s
        for s in case["context"]["normalized_content"]["sections"]
        if s["key"] == "condition"
    )
    soup = BeautifulSoup(condition["html"], "html.parser")
    cells = soup.find_all("tr")[1].find_all("td")
    cells[1].string = "0,02"
    cells[-1].string = "0,004"
    condition["html"] = str(soup)
    with pytest.raises(ValueError):
        _plan(case, case["context"])
