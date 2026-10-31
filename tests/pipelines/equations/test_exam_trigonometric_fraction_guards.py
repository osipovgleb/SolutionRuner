"""Bound the new fraction shapes and refuse inconsistent source equations."""

import json
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest
import sympy as sp

from solution_runner.pipelines.equations.exam_trigonometric import analyze
from solution_runner.pipelines.equations.exam_trigonometric_auxiliary_figures import (
    sources,
    validate_system,
)
from solution_runner.pipelines.equations.exam_trigonometric_auxiliary_notes import (
    half_angle,
    split,
)
from solution_runner.pipelines.equations.exam_trigonometric_circle import CIRCLES, read
from solution_runner.pipelines.equations.exam_trigonometric_compile import C, S
from solution_runner.pipelines.equations.exam_trigonometric_methods import (
    compile_reviewed,
    parse_equation,
)
from solution_runner.pipelines.word_problems.common import UnsupportedCondition

DATA = json.loads(
    (
        Path(__file__).parent
        / "fixtures/category_14_trigonometric_fraction_domains.json"
    ).read_text()
)
EXAMPLE = next(c for c in DATA["cases"] if c["task"] == "501215")["context"]
PARENT = next(
    s["html"]
    for s in EXAMPLE["normalized_content"]["sections"]
    if s["key"] == "solution"
)


def primary():
    _, f, i, b = read(EXAMPLE)
    return analyze(f, i, b, PARENT)


@pytest.mark.parametrize(
    "formula",
    [
        r"\frac{\cos x}{(\tg x-1)^3}=0",
        r"\frac{\cos x}{\tg x-1}+\frac{1}{\cos x}=0",
        r"\frac{\cos x}{\tg(2x)-1}=0",
        r"\frac{\cos^3 x+1}{\tg x-1}=0",
        r"\frac{\cos x}{\tg^4 x+1}=0",
    ],
)
def test_unreviewed_fraction_shapes_fail_closed(formula):
    with pytest.raises(UnsupportedCondition):
        compile_reviewed(formula, C, sp.S.One)


@pytest.mark.parametrize(
    "formula", [r"\operatorname{foottg}x=1", r"\operatorname{sinx}x=1"]
)
def test_unknown_operator_names_are_not_repaired_into_trigonometric_functions(formula):
    with pytest.raises(UnsupportedCondition):
        parse_equation(formula)


def test_numbered_notes_do_not_allow_missing_methods_or_extra_figures():
    from bs4 import BeautifulSoup

    for fragment in ("формулы двойных углов", "вспомогательного угла"):
        with pytest.raises(UnsupportedCondition, match="all three reviewed"):
            split(PARENT.replace("\xad", "").replace(fragment, "неизвестный метод"))
    soup = BeautifulSoup(PARENT, "html.parser")
    soup.find_all("img")[1].decompose()
    with pytest.raises(UnsupportedCondition, match="all three reviewed"):
        split(str(soup))


@pytest.mark.parametrize(
    "change",
    [
        {"scale": sp.S.One},
        {"scale": sp.Integer(3)},
        {"raw": S + 2 * C + 1},
        {"poles": (C,)},
        {"translation": sp.S.One},
    ],
)
def test_half_angle_note_requires_its_original_domain_and_exact_identity(change):
    with pytest.raises(UnsupportedCondition, match="equal-magnitude"):
        half_angle(replace(primary(), **change))


@pytest.mark.parametrize(
    "field,value",
    [
        ("circle_scale", "1"),
        ("equation_coefficients", ["1", "-1", "1"]),
        ("residues", ["1"]),
        ("bounds", ["0", "2", True, False]),
    ],
)
def test_system_figure_cannot_stand_in_for_a_different_equation_or_interval(
    field, value
):
    aid = EXAMPLE["normalized_content"]["assets"][1]["asset_id"]
    entry = deepcopy(CIRCLES[aid])
    entry[field] = value
    with pytest.raises(UnsupportedCondition, match="geometric system"):
        validate_system(entry, primary())


def test_missing_companion_reversed_figures_or_changed_identity_fail_closed():
    for mutate in ("missing", "reversed", "url"):
        context = deepcopy(EXAMPLE)
        assets = context["normalized_content"]["assets"]
        if mutate == "missing":
            assets.pop(0)
        elif mutate == "reversed":
            assets.reverse()
        else:
            assets[1]["url"] = "/assets/changed"
        with pytest.raises(UnsupportedCondition):
            sources(context)


def test_source_mismatch_is_not_reinterpreted_as_the_periodic_equation_in_its_solution():
    example = DATA["rejected_cases"][0]
    _, formula, _, _ = read(example["context"])
    assert example["group"] == "519472" and r"\cos^2 x-\frac{x}{2}" in formula
    with pytest.raises(UnsupportedCondition):
        compile_reviewed(formula, C, sp.S.One)
