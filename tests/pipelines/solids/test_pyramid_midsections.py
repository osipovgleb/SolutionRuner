"""Independent valid sections and the explicitly impossible source condition."""

from copy import deepcopy
from dataclasses import replace

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from midpoint_source_cases import replay, section, solution_html
from midsection_geometry_oracle import verify
from pyramid_midsection_source_cases import BLOCKED, CASES, plan, read

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.solids.distance_figures import prepare
from solution_runner.pipelines.solids.spatial_distance_model import condition_text

EXPECTED = {
    "509948": 44,
    "510107": 104,
    "511602": 4 * sp.sqrt(177) / 9,
    "513095": 12,
    "512357": sp.Rational(23, 4),
    "512399": sp.Rational(23, 2),
    "513347": sp.Rational(9, 2),
    "513366": 9,
    "501690": 85 * sp.sqrt(2),
    "501945": 5 * sp.sqrt(2),
    "501730": sp.Rational(2, 3),
    "511367": 20 * sp.sqrt(2),
    "504416": 4 * sp.sqrt(59) / 5,
    "504437": 4 * sp.sqrt(23) / 3,
}


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_native_geometry_every_equality_exact_figures_and_repeat(case):
    ctx = deepcopy(case["context"])
    result = plan(case, ctx)
    m = prepare(ctx, ())[0]
    assert sp.simplify(m.answer - EXPECTED[case["task"]]) == 0
    assert sp.simplify(verify(solution_html(result), m) - m.answer) == 0
    assert ctx == case["context"]
    updated = deepcopy(ctx)
    replay(updated, result.transformations)
    assert not plan(case, updated).transformations
    for key in ("condition", "source", "criteria"):
        assert section(updated, key) == section(ctx, key)
    assert (
        updated["normalized_content"]["assets"] == ctx["normalized_content"]["assets"]
    )
    soup = BeautifulSoup(solution_html(result), "html.parser")
    assert len(soup.find_all("img")) == 1
    assert len(soup.select('ol[data-layout="source-subparts"] > li')) == 2


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize(
    "suffix", (" Найдите также объём.", " Докажите дополнительное утверждение.")
)
def test_extra_unread_request_is_refused(case, suffix):
    ctx = deepcopy(case["context"])
    section(ctx, "condition")["html"] += "<p>" + suffix + "</p>"
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_parent_method_pin_drift_is_refused(case):
    with pytest.raises(ContentPlanError):
        plan(case, parent_solution_html="changed")


@pytest.mark.parametrize(
    "task,old,new",
    (
        ("509948", "в отношении 5: 1", "в отношении 4: 1"),
        ("513095", "медиану CL", "медиану CA"),
        ("512357", "7: 2", "6: 2"),
        ("513347", "BL: LC = 1: 2", "BL: LC = 1: 3"),
        ("501945", "в отношении 2: 1", "в отношении 3: 1"),
        ("501730", "MN: NC = 2: 1", "MN: NC = 1: 1"),
        ("504416", "перпендикулярно ребру SC", "перпендикулярно ребру SA"),
        ("504437", "ребро AB перпендикулярно", "ребро AC перпендикулярно"),
    ),
)
def test_false_ratio_or_changed_section_is_refused(task, old, new):
    case = next(c for c in CASES if c["task"] == task)
    ctx = deepcopy(case["context"])
    raw = condition_text(section(ctx, "condition")["html"], None)
    assert old in raw
    section(ctx, "condition")["html"] = "<p>" + raw.replace(old, new) + "</p>"
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


def scaled(m, factor):
    from solution_runner.pipelines.solids.pyramid_midsection_model import (
        _median,
        _reflected,
        _vertical,
    )
    from solution_runner.pipelines.solids.pyramid_perpendicular_section_model import (
        _solve,
    )

    given = [sp.latex(v * factor) for _, v in m.given]
    if m.mode == "triangle_vertical_section_area":
        return _vertical((*given, m.names[0], "5", "1"))
    if m.mode.startswith("reflected_"):
        square = m.mode == "reflected_square_section_midline"
        return _reflected((given[0], "1" if square else "7", "2", m.names[0]), square)
    if m.mode == "square_median_section_area":
        return _median((*given, "2", "1"), *m.names)
    return _solve(given, m.names[0])


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize("factor", (sp.Rational(1, 3), sp.Integer(2)))
def test_scaled_sections_keep_the_true_area_or_midline_and_auxiliary_names(
    case, factor
):
    from solution_runner.pipelines.solids.spatial_distance_proofs import render

    original = prepare(case["context"], ())[0]
    m = replace(scaled(original, factor), symbols=original.symbols)
    exponent = 1 if m.mode.endswith("midline") else 2
    assert (
        sp.simplify(verify(render(m, {}), m) - factor**exponent * original.answer) == 0
    )


@pytest.mark.parametrize(
    "case", [c for c in CASES if c["group"] == "504416"], ids=lambda c: c["task"]
)
def test_missing_native_answer_is_derived_from_condition(case):
    assert section(case["context"], "answer") is None
    result = plan(case)
    answer = next(
        t
        for t in result.transformations
        if t["transformation_target_id"].startswith("section:answer")
    )
    assert answer["operation"] == "add"
    assert "Примечание" in BeautifulSoup(solution_html(result), "html.parser").text


def test_impossible_native_section_is_only_an_edge_and_does_not_get_the_source_answer():
    case = BLOCKED[0]
    ctx = deepcopy(case["context"])
    # The other two vertices lie strictly on the same side of the AB plane.
    a, e = sp.Integer(3), sp.Integer(2)
    r = a / sp.sqrt(3)
    A = sp.Matrix([r, 0, 0])
    B = sp.Matrix([-r / 2, a / 2, 0])
    C = sp.Matrix([-r / 2, -a / 2, 0])
    S = sp.Matrix([0, 0, 1])
    normal = S - C
    assert sp.simplify((B - A).dot(normal)) == 0
    assert (C - A).dot(normal) < 0 and (S - A).dot(normal) < 0
    assert a * a / (2 * e * e) == sp.Rational(9, 8)
    with pytest.raises(ContentPlanError, match="only along AB"):
        plan(case, ctx)
    assert ctx == case["context"]


def test_plain_perpendicular_request_uses_the_geometry_reader_after_box_refusal():
    case = BLOCKED[0]
    ctx = deepcopy(case["context"])
    raw = (
        condition_text(section(ctx, "condition")["html"], None)
        .replace("SA = 2", "SA = 5")
        .replace("AB = 3", "AB = 4")
    )
    section(ctx, "condition")["html"] = "<p>" + raw + "</p>"
    m = read(ctx)
    assert m.names == ("plain",)
    assert (
        sp.simplify(verify(solution_html(plan(case, ctx)), m) - 4 * sp.sqrt(59) / 5)
        == 0
    )


def test_existing_plain_box_success_does_not_enter_the_new_section_reader(monkeypatch):
    from solution_runner.pipelines.solids import spatial_distance_model as reader

    sentinel = object()
    monkeypatch.setattr(reader, "read_box", lambda *_: sentinel)

    def unexpected(*_):
        raise AssertionError("the old successful box path changed")

    monkeypatch.setattr(reader, "condition_text", unexpected)
    assert reader.read_question("<p>Найдите расстояние.</p>") is sentinel
