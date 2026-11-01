"""Boundary roots and integer bindings are independent of saved source answers."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import sympy as sp

from solution_runner.pipelines.equations.exam_trigonometric import analyze, select
from solution_runner.pipelines.equations.exam_trigonometric_proof import series_lines
from solution_runner.pipelines.equations.exam_trigonometric_radical_product import (
    admissible_factor,
    shifted_operands,
)
from solution_runner.pipelines.equations.exam_trigonometric_variants import (
    root_notation,
)
from solution_runner.pipelines.word_problems.common import section

DATA = json.loads(
    (
        Path(__file__).parent
        / "fixtures/category_14_trigonometric_ratio_square_root_factors.json"
    ).read_text()
)
PARENT = section(
    next(
        e["context"]["normalized_content"]
        for e in DATA["cases"]
        if e["task"] == "653512"
    ),
    "solution",
)["html"]
R = sp.Rational


def model(formula):
    return analyze(formula, r"[0;2\pi)", (sp.S.Zero, 2 * sp.pi, True, False), PARENT)


def test_the_common_notation_pass_binds_an_already_named_family():
    a = SimpleNamespace(
        series=((R(1, 3), sp.Integer(2)),),
        family_parameters=("n",),
        parameter="k",
        sine_inverse=False,
        restricted_families=(),
    )
    text = series_lines(a.series)[0]
    named = text.replace("k", "n")
    old = named + r",\quad k\in\mathbb Z"
    expected = named + r",\quad n\in\mathbb Z"
    assert root_notation(a, (old, old, old)) == (expected, expected, expected)


@pytest.mark.parametrize(
    "formula",
    [
        r"(\sin x)(\sqrt{\tg x}-1)=0",
        r"(\sin x)(1-\sqrt{\tg x})=0",
        r"(1-\sqrt{\tg x})(\sin x)=0",
    ],
)
def test_zero_first_factor_at_zero_radicand_is_not_lost_by_the_new_case(formula):
    a = model(formula)
    assert shifted_operands(formula) is None
    assert shifted_operands(formula, allow_vanishing=True)[2] == -1
    assert set(select(a.series, (sp.S.Zero, sp.Integer(2), True, False))[0]) == {
        sp.S.Zero,
        R(1, 4),
        sp.S.One,
        R(5, 4),
    }
    assert admissible_factor(a)[1] == 1


def test_zero_radicand_alone_is_not_a_root_of_a_vanishing_offset_product():
    a = model(r"(\cos x)(\sqrt{\tg x}-1)=0")
    assert select(a.series, (sp.S.Zero, sp.Integer(2), True, False))[0] == (
        R(1, 4),
        R(5, 4),
    )
    assert sp.S.Zero not in a.residues and sp.S.One not in a.residues
