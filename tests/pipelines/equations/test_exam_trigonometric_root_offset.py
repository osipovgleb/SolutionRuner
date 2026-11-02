"""Restore a verified root boundary and keep domain and selection figures separate."""

import gzip
import hashlib
import json
import math
from copy import deepcopy
from pathlib import Path
from xml.etree import ElementTree as ET

import mpmath as mp
import pytest
import sympy as sp
from bs4 import BeautifulSoup

from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.equations.exam_trigonometric import analyze, select
from solution_runner.pipelines.equations.exam_trigonometric_circle import (
    CIRCLES,
    DIRECTORY,
    read,
    validate,
)
from solution_runner.pipelines.equations.exam_trigonometric_compile import C, S
from solution_runner.pipelines.equations.exam_trigonometric_proof import render
from solution_runner.pipelines.equations.verified_expression_repair import (
    repair_verified_condition,
)
from solution_runner.pipelines.word_problems.common import UnsupportedCondition, section

DATA = json.loads(
    (
        Path(__file__).parent / "fixtures/category_14_trigonometric_root_offset.json"
    ).read_text()
)
CASE = DATA["cases"][0]
CONTEXT = CASE["context"]
PARENT = section(CONTEXT["normalized_content"], "solution")["html"]
HANDLER = get_handler(get_group_profile(CASE["group"]).content_rule_key)
FIGURES = tuple(a["asset_id"] for a in CONTEXT["normalized_content"]["assets"])
FORMULA = r"(2\cos x+1)(\sqrt{-\sin x}-1)=0."


def plan(context=None, parent=PARENT):
    return HANDLER.plan(PlanInput(context or CONTEXT, parent_solution_html=parent))


def analysis(formula=None):
    ctx, _ = repair_verified_condition(CONTEXT, validate=read)
    _, source, interval, bounds = read(ctx)
    return analyze(formula or source, interval, bounds, PARENT)


def test_verified_repair_is_exact_and_independent_of_task_identity_or_saved_answers():
    before = deepcopy(CONTEXT)
    ctx = deepcopy(before)
    ctx["source_problem_id"] = "unrelated-id"
    for key in ("answer", "solution"):
        section(ctx["normalized_content"], key)["html"] = "<p>UNUSED 987654</p>"
    actual = plan(ctx)
    assert actual == plan()
    assert actual.condition_html.count(FORMULA) == 1
    assert r"\sqrt{-\sin x-1}" not in actual.condition_html
    assert [
        t["transformation_target_id"].split(":")[1] for t in actual.transformations
    ] == ["condition", "answer", "solution"]
    assert CONTEXT == before
    assert HANDLER.diagram_specs(CONTEXT) == ()


def test_local_replay_is_empty_and_keeps_both_original_asset_identities():
    ctx = deepcopy(CONTEXT)
    prepared = plan()
    for t in prepared.transformations:
        assert not t["transformation_target_id"].startswith("asset:")
        next(
            s
            for s in ctx["normalized_content"]["sections"]
            if s["transformation_target_id"] == t["transformation_target_id"]
        ).update(t["value"])
    assert plan(ctx).transformations == ()
    assert (
        ctx["normalized_content"]["assets"] == CONTEXT["normalized_content"]["assets"]
    )
    assert section(ctx["normalized_content"], "solution")["asset_keys"] == [
        "image_1",
        "image_2",
    ]


def test_original_equation_domain_and_root_offset_are_checked_independently():
    a = analysis()
    assert a.radical_product.radicand == -S
    assert a.radical_product.root_offset == -1
    assert a.radical_product.factor == 2 * C + 1
    assert a.residues == a.selected == (sp.Rational(4, 3), sp.Rational(3, 2))
    assert select(a.series, (0, 2, True, False))[0] == a.residues
    with mp.workdps(65):
        for n in range(-216, 217):
            q = sp.Rational(n, 48)
            x = mp.mpf(n) * mp.pi / 48
            radicand = -mp.sin(x)
            if abs(radicand) < mp.mpf("1e-55"):
                radicand = mp.mpf(0)
            expected = radicand >= 0 and abs(
                (2 * mp.cos(x) + 1) * (mp.sqrt(radicand) - 1)
            ) < mp.mpf("1e-50")
            assert expected == (q % 2 in a.residues)
    assert sp.Rational(2, 3) not in a.residues
    assert not {sp.S.Zero, sp.S.One} & set(a.residues)
    assert select(a.series, (0, sp.Rational(3, 2), True, False))[0] == (
        sp.Rational(4, 3),
    )


def test_both_figures_keep_their_original_order_placement_and_distinct_roles():
    p = plan()
    soup = BeautifulSoup(p.solution_html, "html.parser")
    images = soup.find_all("img")
    assert [n["data-asset-id"] for n in images] == list(FIGURES)
    assert images[0].find_parent("li") is None
    second = images[1].find_parent("li")
    assert second["data-list-marker"] == "б)"
    assert second.find("img") is images[1]
    assert images[1].parent is next(
        n for n in second.children if getattr(n, "name", None)
    )
    assert images[0]["alt"] == "Окружность для проверки ОДЗ"
    assert images[1]["alt"] == "Окружность для отбора корней"
    text = soup.get_text(" ", strip=True)
    assert "Корень не определён" in text and "Нулевой радикал сам по себе" in text
    formulas = [n["data-inline-latex"] for n in soup.select("[data-inline-latex]")]
    assert any(r"\sqrt{" in f and "}-1=0" in f for f in formulas)
    assert not any(r"\right)\left(1-\sqrt{" in f for f in formulas)


@pytest.mark.parametrize("identifier", FIGURES)
def test_native_svg_root_markers_and_crosses_are_preserved(identifier):
    entry = CIRCLES[identifier]
    raw = gzip.decompress((DIRECTORY / (identifier + ".svgz")).read_bytes())
    assert hashlib.sha256(raw).hexdigest() == entry["sha256"]
    root = ET.fromstring(raw)
    paths = {e.get("d") for e in root.iter() if e.tag.endswith("path")}
    for p in (*entry["green_markers"], *entry["excluded_markers"]):
        assert p["path_d"] in paths
        frame = p["native_frame"]
        assert frame["path_d"] in paths
        angle = float(sp.Rational(p["angle"])) * math.pi
        distance = math.hypot(
            p["x"] - frame["cx"] - frame["rx"] * math.cos(angle),
            p["y"] - frame["cy"] + frame["ry"] * math.sin(angle),
        )
        assert distance < (1.3 if p in entry["excluded_markers"] else 0.8)
        for cross in p.get("cross_segments", []):
            assert any(
                n.tag.endswith(cross["tag"]) and dict(n.attrib) == cross["attributes"]
                for n in root.iter()
            )
    assert len(entry["green_markers"]) == 2
    if identifier == FIGURES[0]:
        assert entry["selection_kind"] == "all_roots"
        assert entry["bounds"] is None and entry["labels"] == []
        assert entry["selection_companion"] == FIGURES[1]
        assert [p["angle"] for p in entry["excluded_markers"]] == ["2/3"]
        assert len(entry["excluded_markers"][0]["cross_segments"]) == 2
    else:
        assert entry["bounds"] == ["0", "3/2", True, True]
        assert entry["labels"] == ["4/3", "3/2"]
    validate(entry, analysis())


def test_domain_shading_keeps_the_two_original_upper_quarters():
    entry = CIRCLES[FIGURES[0]]
    region = entry["excluded_region"]
    assert region["condition"] == "s > 0"
    raw = gzip.decompress((DIRECTORY / (FIGURES[0] + ".svgz")).read_bytes())
    root = ET.fromstring(raw)
    shapes = region["paths"]
    assert len(shapes) == 2
    cx, cy, radius = entry["circle"]
    for shape in shapes:
        assert any(dict(n.attrib) == shape["attributes"] for n in root.iter())
        xmin, xmax, ymin, ymax = shape["bounds"]
        assert ymax < cy + 0.2 and abs(ymin - (cy - radius)) < 0.4
        assert xmin < cx + 0.5 and xmax > cx - 0.5
    assert abs(sum(s["area"] for s in shapes) / (math.pi * radius**2 / 2) - 1) < 0.02
    assert analysis().domain == -S


@pytest.mark.parametrize(
    "field,value", [("radicand", "s"), ("root_offset", "-2"), ("poles", ["c"])]
)
def test_paired_figures_require_the_exact_original_radical_domain(field, value):
    entry = deepcopy(CIRCLES[FIGURES[0]])
    entry["radical_product_domain"][field] = value
    with pytest.raises(UnsupportedCondition):
        validate(entry, analysis())


@pytest.mark.parametrize(
    "change", ["missing", "swapped", "extra", "unknown", "wrong-url"]
)
def test_changed_asset_sets_cannot_reuse_the_audited_pair(change):
    ctx = deepcopy(CONTEXT)
    assets = ctx["normalized_content"]["assets"]
    if change == "missing":
        assets.pop()
    elif change == "swapped":
        assets.reverse()
    elif change == "extra":
        assets.append(dict(assets[0], asset_key="image_3"))
    elif change == "unknown":
        assets[1]["asset_id"] = "unknown"
        assets[1]["url"] = "/assets/unknown"
    else:
        assets[1]["url"] = "/assets/unknown"
    with pytest.raises(UnsupportedCondition):
        plan(ctx)


@pytest.mark.parametrize(
    "change", ["missing", "swapped", "wrong-marker", "extra", "wrong-identity"]
)
def test_changed_parent_figure_roles_are_rejected(change):
    soup = BeautifulSoup(PARENT, "html.parser")
    images = soup.find_all("img")
    if change == "missing":
        images[0].parent.decompose()
    elif change == "swapped":
        images[0].parent.insert_before(images[1].parent.extract())
    elif change == "wrong-marker":
        images[1].parent.find_next_sibling().string = "а) Другая часть решения"
    elif change == "wrong-identity":
        images[1]["data-asset-id"] = "unknown"
    else:
        soup.append(deepcopy(images[0].parent))
    with pytest.raises(UnsupportedCondition):
        plan(parent=str(soup))


def test_repair_requires_exact_damaged_html_and_selection_requires_original_interval():
    ctx = deepcopy(CONTEXT)
    condition = section(ctx["normalized_content"], "condition")
    condition["html"] = condition["html"].replace("Ре­ши­те", "Решите")
    unchanged, change = repair_verified_condition(ctx, validate=read)
    assert unchanged is ctx and change is None
    with pytest.raises(UnsupportedCondition):
        plan(ctx)
    entry = deepcopy(CIRCLES[FIGURES[1]])
    entry["bounds"][1] = "2"
    with pytest.raises(UnsupportedCondition):
        validate(entry, analysis())


@pytest.mark.parametrize(
    "formula,full",
    [
        (r"(2\cos x-1)(\sqrt{-\sin x}-1)=0", ("3/2", "5/3")),
        (r"(2\cos x+\sqrt{2})(\sqrt{-\sin x}-1)=0", ("5/4", "3/2")),
        (r"(\cos x+1)(\sqrt{-\sin x}-1)=0", ("1", "3/2")),
    ],
)
def test_existing_root_offset_kernel_is_reused_for_other_coefficients(formula, full):
    a = analysis(formula)
    assert a.residues == tuple(map(sp.Rational, full))
    assert render(a, "")[2].count("Во втором случае") == 1


def test_profile_uses_the_exact_catalog_binding_and_existing_handler():
    p = get_group_profile(CASE["group"])
    assert p.source_group_id == DATA["group"]["uuid"]
    assert p.snapshot_theme_id == DATA["group"]["theme_uuid"]
    assert p.group_order_index == DATA["group"]["order_index"]
    assert p.content_rule_key == "exam-trigonometric-polynomial-circle"
