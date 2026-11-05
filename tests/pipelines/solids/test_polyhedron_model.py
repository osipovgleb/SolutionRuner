"""Prove volume witnesses against an independent hull and unchanged source conditions."""

import itertools
import json
from pathlib import Path

import pytest
import sympy as sp
from midpoint_source_cases import section
from polyhedron_volume_oracle import volume

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.equations.power_arithmetic import ScalarParser
from solution_runner.pipelines.solids.box_coordinates import VERTICES
from solution_runner.pipelines.solids.polyhedron_geometry import recognize
from solution_runner.pipelines.solids.polyhedron_input import complete_text
from solution_runner.pipelines.solids.polyhedron_model import read_question

DATA = json.loads(
    (Path(__file__).parent / "fixtures/category_3_polyhedron_sources.json").read_text()
)
CASES = DATA["cases"]
UNSUPPORTED = set(DATA["unsupported_tasks"])
EVIDENCE = json.loads(
    (
        Path(__file__).parent / "fixtures/polyhedron_underdetermined_evidence.json"
    ).read_text()
)
SETS = [names for size in (4, 5, 6) for names in itertools.combinations(VERTICES, size)]


def read(case):
    assets = case["context"]["normalized_content"]["assets"]
    source = next((a["asset_id"] for a in assets if a["asset_key"] == "image_1"), None)
    return read_question(section(case["context"], "condition")["html"], source)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_every_original_condition_answer_or_underdetermination(case):
    if case["task"] in UNSUPPORTED:
        with pytest.raises(ContentPlanError, match="oblique"):
            read(case)
        return
    m = read(case)
    answer = section(case["context"], "answer")["html"]
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(answer, "html.parser")
    tex = soup.select_one("[data-inline-latex]")
    value = tex["data-inline-latex"] if tex else soup.get_text(strip=True)
    assert sp.simplify(m.answer - ScalarParser(value).parse()) == 0
    assert m.solid.fraction == sp.Rational(
        volume([VERTICES[n] for n in m.solid.vertices])
    )
    assert m.answer == m.box_volume * m.solid.fraction
    if m.squares:
        points = [
            tuple(x * sp.sqrt(v) for x, v in zip(VERTICES[n], m.squares))
            for n in m.solid.vertices
        ]
        assert sp.Rational(volume(points)) == m.answer


@pytest.mark.parametrize("names", SETS)
def test_all_four_to_six_vertex_subsets_have_exact_proof_witness_or_fail_closed(names):
    expected = sp.Rational(volume([VERTICES[n] for n in names]))
    try:
        m = recognize(names)
    except ContentPlanError:
        assert len(names) > 4 or expected == 0
        return
    assert m.fraction == expected > 0
    assert set(itertools.chain.from_iterable(m.faces)) == set(names)
    edge_faces = {}
    for face in m.faces:
        for a, b in zip(face, face[1:] + face[:1]):
            edge_faces.setdefault(tuple(sorted((a, b))), 0)
            edge_faces[tuple(sorted((a, b)))] += 1
    assert set(edge_faces.values()) == {2}
    if m.kind == "pyramid":
        assert all(VERTICES[n][m.axis] == VERTICES[m.foot][m.axis] for n in m.base)
        assert VERTICES[m.apex][m.axis] != VERTICES[m.foot][m.axis]
        assert sum(abs(x - y) for x, y in zip(VERTICES[m.apex], VERTICES[m.foot])) == 1
    elif m.kind == "prism":
        assert all(
            sum(abs(x - y) for x, y in zip(VERTICES[a], VERTICES[b])) == 1
            for a, b in zip(m.base, m.upper)
        )


def test_supported_shape_counts_and_independent_oracle_scaling():
    counts = {}
    for names in SETS:
        try:
            m = recognize(names)
        except ContentPlanError:
            continue
        counts[m.kind] = counts.get(m.kind, 0) + 1
    assert counts == {"pyramid": 80, "central_tetrahedron": 2, "prism": 12}
    assert volume([(0, 0, 0), (2, 0, 0), (0, 3, 0), (0, 0, 4)]) == 4
    assert (
        volume([tuple(x * s for x, s in zip(p, (2, 3, 4))) for p in VERTICES.values()])
        == 24
    )
    assert volume([(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)]) == 0


def test_prism_inside_tetrahedron_group_uses_its_real_vertices():
    a = read(next(c for c in CASES if c["task"] == "245336"))
    b = read(next(c for c in CASES if c["task"] == "661012"))
    assert a.solid.kind == "pyramid" and a.solid.fraction == sp.Rational(1, 6)
    assert (
        b.solid.kind == "prism"
        and b.solid.fraction == sp.Rational(1, 2)
        and b.answer == 120
    )


def test_base_and_height_follow_actual_vertices_and_parent_horizontal_method():
    m = read(next(c for c in CASES if c["task"] == "245338"))
    assert m.solid.base == ("A", "B", "C") and m.solid.apex == "B_1"
    changed = read(next(c for c in CASES if c["task"] == "265013"))
    assert changed.solid.base == ("A", "B", "C", "D") and changed.solid.apex == "D_1"
    assert changed.solid.foot == "D" and changed.box_volume == 48


@pytest.mark.parametrize(
    "names",
    [
        ("A", "A", "B", "C"),
        ("A", "B", "C", "Z"),
        ("A", "B", "C"),
        ("A", "B", "C", "D"),
        tuple(VERTICES),
    ],
)
def test_duplicate_unknown_degenerate_or_unreviewed_shape_rejected(names):
    with pytest.raises(ContentPlanError):
        recognize(names)


def condition(given="AB=2, AD=3, AA_1=4", points="A, B, C, B_1"):
    return f"<p>Найдите объем многогранника, вершинами которого являются точки {points} прямоугольного параллелепипеда ABCDA_1B_1C_1D_1, у которого {given}.</p>"


@pytest.mark.parametrize(
    "change",
    [
        lambda h: h.replace("AB=2", "AB=0"),
        lambda h: h.replace("AB=2", "AB=-2"),
        lambda h: h.replace("AB=2", "AB=\\frac{1}{0}"),
        lambda h: h.replace("AB=2", "AC=2"),
        lambda h: h.replace("AA_1=4", "BC=3"),
        lambda h: h.replace("A, B, C, B_1", "A, B, C, A"),
        lambda h: h + "<p>Округлите до сотых.</p>",
        lambda h: h.replace("прямоугольного ", ""),
        lambda h: h.replace("AA_1=4", "AA_1=4, BB_1=4"),
    ],
)
def test_incomplete_impossible_or_unknown_complete_condition_rejected(change):
    with pytest.raises(ContentPlanError):
        read_question(change(condition()))


def test_fractional_and_radical_edges_remain_exact():
    m = read_question(condition(r"AB=\frac{1}{2}, AD=\sqrt{2}, AA_1=3"))
    assert m.answer == sp.sqrt(2) / 4


def test_arbitrary_positive_affine_total_volume_does_not_assume_right_angles():
    html = r"<p>Объем параллелепипеда ABCDA_1B_1C_1D_1 равен \frac{7}{2}. Найдите объем треугольной пирамиды AD_1CB_1.</p>"
    assert read_question(html).answer == sp.Rational(7, 6)
    for bad in ("0", "-2", r"\sqrt{-1}", r"\frac{1}{0}"):
        with pytest.raises(ContentPlanError):
            read_question(html.replace(r"\frac{7}{2}", bad))


def test_explicit_rectangular_footer_outside_paragraph_is_read_and_required():
    html = condition().replace("прямоугольного ", "")
    assert read_question(html + "<i>Параллелепипед прямоугольный.</i>").answer == 4
    with pytest.raises(ContentPlanError):
        read_question(html)


@pytest.mark.parametrize(
    "markup",
    [
        "<i>ABCDA</i><sub>2</sub>",
        "<i>ABCDA</i><sub><b>1</b></sub>",
        '<var data-math-identifier="ABCDA"><b>ABCDA</b></var><sub>1</sub>',
        '<var data-math-identifier="XYZ">XYZ</var><sub>1</sub>',
    ],
)
def test_nested_unknown_or_nonunit_vertex_subscripts_are_not_guessed(markup):
    with pytest.raises(ContentPlanError):
        complete_text("<p>" + markup + "</p>")


def test_primary_evidence_identifies_the_underdetermined_conditions():
    assert {e["task"] for e in EVIDENCE} == UNSUPPORTED
    for e in EVIDENCE:
        assert len(e["html_sha256"]) == 64 and e["url"].endswith("=" + e["task"])
        assert len(e["condition_sha256"]) == 64
        assert e["condition_has_rectangular_assumption"] is False
        assert len(e["formula_alts"]) >= 5


@pytest.mark.parametrize(
    "html",
    [
        "<p>Дан прямоугольный параллелепипед ABCDA_1B_1C_1D_1, длины его ребер AB=2, AD=3, AA_1=4. Найдите объем призмы ABCB_1.</p>",
        "<p>Объем параллелепипеда ABCDA_1B_1C_1D_1 равен 12. Найдите объем треугольной пирамиды ABDA_1B_1D_1.</p>",
    ],
)
def test_declared_solid_type_must_match_the_actual_vertices(html):
    with pytest.raises(ContentPlanError, match="geometric type"):
        read_question(html)
