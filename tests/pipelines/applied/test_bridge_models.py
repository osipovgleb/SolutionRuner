"""Bridge substitution, compatible source figures and all three parent notes."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from test_algebraic_formulas import (
    test_shared_scalar_rule_registration as verify_registration,
)
from test_algebraic_formulas import (
    test_source_answers_are_computed_without_mutation_and_idempotently as verify_source,
)
from test_algebraic_formulas import (
    test_unread_instructions_and_foreign_assets_cannot_be_ignored as verify_rejection,
)
from test_physical_polynomials import plan, solution

from solution_runner.pipelines.applied import bridge_assets, bridge_proof
from solution_runner.pipelines.applied import physical_polynomials as model
from solution_runner.pipelines.applied.physical_questions import parse
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler

DATA = json.loads(
    (Path(__file__).parent / "fixtures/category_10_bridge.json").read_text()
)
CASES = DATA["cases"]


def sample(task):
    return next(c for c in CASES if c["task"] == task)


def changed(old, new):
    text = bridge_assets.read(sample("324467")["context"])[3]
    assert old in text
    return model.analyze(parse(text.replace(old, new)))


@pytest.mark.parametrize("group", DATA["groups"], ids=lambda g: g["key"])
def test_bridge_extends_the_shared_polynomial_rule(group):
    verify_registration(group)
    assert (
        get_group_profile(group["key"]).content_rule_key
        == get_group_profile("27955").content_rule_key
    )


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_source_answers_are_computed_without_mutation_and_replay_is_idempotent(case):
    verify_source(case)
    prepared = plan(case, case["context"])
    original = next(
        s["html"]
        for s in case["context"]["normalized_content"]["sections"]
        if s["key"] == "condition"
    )
    assert prepared.condition_html == original
    assert not any(
        t["transformation_target_id"].startswith("asset:")
        for t in prepared.transformations
    )
    html = solution(prepared)
    assert bridge_assets.TYPES in html and bridge_assets.SCHEME not in html
    assert (
        html.index("Примечание 1")
        < html.index("Примечание 2")
        < html.index("Примечание 3")
        < html.index(bridge_assets.TYPES)
    )
    assert "цепной линией" in html and "веерный" in html and "арфовый" in html
    assert r"e^{x\div a}" in html
    change = next(
        t
        for t in prepared.transformations
        if t["transformation_target_id"].startswith("section:solution")
    )
    assert len(change["value"]["asset_keys"]) == 1


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize("leading", [True, False])
def test_unknown_instructions_and_foreign_assets_are_refused(case, leading):
    verify_rejection(case, leading)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_minimum_and_symmetry_are_recomputed_for_every_law(case):
    _, a = model.calculate(case["context"])
    q = a.question
    vertex, minimum = a.measurements
    assert q.expression.diff(q.variable).subs(q.variable, vertex) == 0
    assert (
        q.expression.subs(q.variable, a.physical_end - q.values["distance"]) == a.result
    )
    assert q.expression.subs(q.variable, vertex) == minimum
    html = solution(plan(case, case["context"]))
    if case["task"] == "324467":
        assert (vertex, minimum) == (74, -sp.Rational(119, 50))
        assert "ниже полотна" in html
    else:
        assert minimum > 0 and "выше полотна" in html and "ниже полотна" not in html
    assert sp.latex(vertex) in html and sp.latex(minimum) in html


def test_endpoints_mirrored_distance_and_touching_deck_are_handled():
    assert changed("в 30 метрах", "в 0 метрах").result == 25
    assert changed("в 30 метрах", "в 148 метрах").result == 25
    assert changed("в 30 метрах", "в 118 метрах").result == sp.Rational(73, 10)
    touch = changed("+25", "+27{,}38")
    assert touch.measurements == (74, 0)
    assert "касается уровня полотна" in bridge_proof.proof(touch)


@pytest.mark.parametrize(
    "old,new,error",
    [
        ("в 30 метрах", "в -1 метрах", "between its pylons"),
        ("в 30 метрах", "в 149 метрах", "between its pylons"),
        ("в 30 метрах", "в 74 метрах", "cannot be negative"),
        ("0{,}005x^{2}", "-0{,}005x^{2}", "sagging bridge"),
        ("-0{,}74x", "+0{,}74x", "sagging bridge"),
        ("0{,}005x^{2}", "0{,}005x^{3}", "quadratic"),
        ("+25", r"+\frac{25x}{x}", "original variable denominators"),
        ("x и y измеряются в метрах", "x и y измеряются в сантиметрах", "recognized"),
    ],
)
def test_nonphysical_points_and_unrecognized_laws_fail_closed(old, new, error):
    with pytest.raises(ValueError, match=error):
        changed(old, new)


def test_required_terminology_figure_is_selected_purely_and_uses_its_exact_source_id():
    case = sample("325722")
    context = deepcopy(case["context"])
    original = deepcopy(context)
    handler = get_handler(get_group_profile(case["group"]).content_rule_key)
    required = handler.asset_requirements(context)
    assert context == original
    assert required == (
        {
            "source_asset_id": bridge_assets.TYPES,
            "section_id": "solution:1",
            "alt_text": bridge_assets.ALT,
        },
    )
    for asset in DATA["source_assets"]:
        assert asset["sha256"] == bridge_assets.HASHES[asset["asset_id"]]
        assert asset["url"] == "/assets/" + asset["asset_id"]


@pytest.mark.parametrize(
    "mode",
    [
        "identity",
        "url",
        "checksum",
        "role",
        "invisible",
        "extra_image",
        "wrong_key",
        "duplicate_metadata",
        "missing_reference",
        "duplicate_reference",
    ],
)
def test_unknown_changed_or_misplaced_figure_cannot_be_silently_discarded(mode):
    case = sample("325722")
    context = deepcopy(case["context"])
    content = context["normalized_content"]
    condition = next(s for s in content["sections"] if s["key"] == "condition")
    if mode == "identity":
        content["assets"][0]["asset_id"] = "foreign"
    elif mode == "url":
        content["assets"][0]["url"] = "https://example.org/bridge.svg"
    elif mode == "checksum":
        content["assets"][0]["sha256"] = "0" * 64
    elif mode == "role":
        next(s for s in content["sections"] if s["key"] == "solution")["asset_keys"] = [
            "image_1"
        ]
    elif mode == "invisible":
        soup = BeautifulSoup(condition["html"], "html.parser")
        soup.img.decompose()
        condition["html"] = str(soup)
    elif mode == "extra_image":
        condition["html"] += '<img src="/assets/foreign"/>'
    elif mode == "wrong_key":
        condition["html"] = condition["html"].replace(
            'data-asset-key="image_1"', 'data-asset-key="image_2"'
        )
    elif mode == "duplicate_metadata":
        content["assets"].append(deepcopy(content["assets"][0]))
    elif mode == "missing_reference":
        condition["asset_keys"] = []
    else:
        condition["asset_keys"] = ["image_1", "image_1"]
    with pytest.raises(ValueError):
        plan(case, context)
