"""Independent coordinate witnesses and source-preserving spatial input checks."""

import itertools
import json
from copy import deepcopy
from pathlib import Path

import pytest
import sympy as sp
from bs4 import BeautifulSoup

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.equations.power_arithmetic import ScalarParser
from solution_runner.pipelines.solids import box_coordinates as coordinates
from solution_runner.pipelines.solids.box_condition_repairs import restore_html
from solution_runner.pipelines.solids.box_distance_model import read_question

DATA = json.loads(
    (
        Path(__file__).parent / "fixtures/category_3_box_distance_sources.json"
    ).read_text()
)
MODES = {
    "245359": "distance_squared",
    "245360": "distance",
    "284357": "edge",
    "284363": "diagonal",
}


def condition(case):
    content = case["context"]["normalized_content"]
    sec = next(s for s in content["sections"] if s["key"] == "condition")
    source = next(
        (
            a["asset_id"]
            for a in content["assets"]
            if a["asset_key"] in sec["asset_keys"]
        ),
        None,
    )
    return sec["html"], source


@pytest.mark.parametrize("case", DATA["cases"], ids=lambda c: c["task"])
def test_all_sixteen_original_questions_match_checked_answers_without_mutation(case):
    before = deepcopy(case)
    m = read_question(*condition(case))
    sec = next(
        s
        for s in case["context"]["normalized_content"]["sections"]
        if s["key"] == "answer"
    )
    soup = BeautifulSoup(sec["html"], "html.parser")
    tag = soup.select_one("[data-inline-latex]")
    saved = tag["data-inline-latex"] if tag else soup.get_text(strip=True)
    assert (
        m.mode == MODES[case["group"]]
        and sp.simplify(
            m.answer - ScalarParser(case.get("expected_answer", saved)).parse()
        )
        == 0
    )
    assert case == before


@pytest.mark.parametrize("pair", list(itertools.combinations(coordinates.VERTICES, 2)))
@pytest.mark.parametrize("square", [False, True])
def test_every_vertex_pair_and_reverse_use_real_scaled_coordinates(pair, square):
    for first, second in (pair, pair[::-1]):
        html = f"<p>Найдите {'квадрат расстояния' if square else 'расстояние'} между вершинами {first} и {second} прямоугольного параллелепипеда, для которого AB=2, AD=3, AA_1=4.</p>"
        m = read_question(html)
        p = sp.diag(2, 3, 4) * sp.Matrix(coordinates.VERTICES[first])
        q = sp.diag(2, 3, 4) * sp.Matrix(coordinates.VERTICES[second])
        expected = (p - q).dot(p - q)
        assert m.squares == (4, 9, 16)
        assert sp.simplify(m.answer - (expected if square else sp.sqrt(expected))) == 0


@pytest.mark.parametrize(
    "given,target,expected",
    [
        (r"BD_1=\sqrt{29}, BC=3, DD_1=4", "CD", 2),
        (r"CA_1=\sqrt{29}, CD=2, B_1B=4", "CB", 3),
        (r"DB_1=\sqrt{29}, BA=2, C_1B_1=3", "CC_1", 4),
        (r"AC=\sqrt{13}, AB_1=\sqrt{20}, AD_1=5", "AA_1", 4),
        (r"AB=\frac{1}{2}, AD=3, AA_1=\sqrt{2}", "A_1C", sp.sqrt(45) / 2),
    ],
)
def test_reversed_parallel_names_and_exact_noninteger_lengths(given, target, expected):
    if target == "A_1C":
        html = f"<p>Найдите расстояние между вершинами A_1 и C прямоугольного параллелепипеда, для которого {given}.</p>"
    else:
        html = f"<p>В прямоугольном параллелепипеде ABCDA_1B_1C_1D_1 известно, что {given}. Найдите длину ребра {target}.</p>"
    assert sp.simplify(read_question(html).answer - expected) == 0


@pytest.mark.parametrize(
    "given",
    [
        "AB=2, CD=2, AA_1=4",
        "AB=2, BA=3, AA_1=4",
        "AB=3, AD=4, BD_1=5",
        "AB=3, AD=4, BD_1=2",
        "AB=0, AD=4, AA_1=2",
        "AB=-1, AD=4, AA_1=2",
        "AB=2, AD=3",
        "AB=2, AD=3, AA_1=4, BC=3",
        "AB=2 AD=3, AA_1=4",
        "AB=12345678901234567890, AD=3, AA_1=4",
    ],
)
def test_degenerate_conflicting_ambiguous_or_incomplete_measurements_fail_closed(given):
    with pytest.raises(ContentPlanError):
        read_question(
            f"<p>Найдите расстояние между вершинами A и C_1 прямоугольного параллелепипеда, для которого {given}.</p>"
        )


@pytest.mark.parametrize(
    "target,kind",
    [("AC", "ребра"), ("AB", "диагонали"), ("AA", "ребра"), ("A_1A_1", "диагонали")],
)
def test_requested_kind_must_match_actual_distinct_vertex_pair(target, kind):
    html = f"<p>В прямоугольном параллелепипеде ABCDA_1B_1C_1D_1 известно, что AB=2, AD=3, AA_1=4. Найдите длину {kind} {target}.</p>"
    with pytest.raises(ContentPlanError):
        read_question(html)


@pytest.mark.parametrize(
    "prefix",
    [
        '<var data-math-identifier="A">A</var><sub>2</sub>',
        '<var data-math-identifier="B">A</var><sub>1</sub>',
        '<var data-math-identifier="A"><em>A</em></var><sub>1</sub>',
        "<i>A</i><sub><b>1</b></sub>",
        "<sub>1</sub>",
    ],
)
def test_subscripts_never_hide_unknown_or_changed_markup(prefix):
    with pytest.raises(ContentPlanError):
        read_question(
            f"<p>Найдите расстояние между вершинами {prefix} и C прямоугольного параллелепипеда, для которого AB=2, AD=3, AA_1=4.</p>"
        )


def test_explicit_subscripts_and_braced_indices_preserve_the_question():
    html = "<p>Найдите расстояние между вершинами <i>А</i><sub>1</sub> и C прямоугольного параллелепипеда, для которого AB=2, AD=3, AA_{1}=4.</p>"
    assert read_question(html).answer == sp.sqrt(29)


def test_exact_primary_source_repair_is_idempotent_and_keeps_original_assets():
    case = next(c for c in DATA["cases"] if c["task"] == "245360")
    html, source = condition(case)
    fixed = restore_html(html)
    assert fixed != html and restore_html(fixed) == fixed
    assert BeautifulSoup(fixed, "html.parser").find("img") == BeautifulSoup(
        html, "html.parser"
    ).find("img")
    assert (
        read_question(fixed, source).requested == "AD_1"
        and read_question(fixed, source).answer == 5
    )
    assert restore_html(html + " ") == html + " "
    with pytest.raises(ContentPlanError):
        read_question(html + " ", source)
    evidence = json.loads(
        (
            Path(__file__).parent / "fixtures/box_distance_subscript_evidence.json"
        ).read_text()
    )
    original = BeautifulSoup(evidence["original_condition_html"], "html.parser")
    assert [(t.parent.get_text(), t["alt"]) for t in original.select("img.tex")] == [
        ("D", "_1"),
        ("AA", "_1"),
    ]


@pytest.mark.parametrize(
    "html",
    [
        None,
        "<p>Найдите расстояние между вершинами A и C_1 параллелепипеда, для которого AB=2, AD=3, AA_1=4.</p>",
        "<p>Найдите расстояние между вершинами A и C_1 прямоугольного параллелепипеда, для которого AB=2, AD=3, AA_1=4. Округлите ответ.</p>",
        '<p><img data-asset-id="unknown" src="/assets/unknown"/>Найдите расстояние между вершинами A и C_1 прямоугольного параллелепипеда, для которого AB=2, AD=3, AA_1=4.</p>',
    ],
)
def test_unknown_condition_or_missing_image_identity_is_rejected(html):
    with pytest.raises(ContentPlanError):
        read_question(html)


@pytest.mark.parametrize(
    "task,saved,expected",
    [("270575", "72", 114), ("271073", "20", 10), ("271075", "5", 13)],
)
def test_saved_answer_errors_do_not_override_actual_vertex_distances(
    task, saved, expected
):
    case = next(c for c in DATA["cases"] if c["task"] == task)
    assert read_question(*condition(case)).answer == expected
    section = next(
        s
        for s in case["context"]["normalized_content"]["sections"]
        if s["key"] == "answer"
    )
    assert BeautifulSoup(section["html"], "html.parser").get_text(strip=True) == saved
    assert case["expected_answer"] == str(expected)
