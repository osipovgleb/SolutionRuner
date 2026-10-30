"""Reviewed SVG transcriptions bind the complete condition, never its saved answer."""

import hashlib
import json
import tomllib
from copy import deepcopy
from pathlib import Path

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from test_category_8_source_samples import CASES, plan

from solution_runner.pipelines.core.numbers import parse_rational
from solution_runner.pipelines.equations.verified_expression_repair import (
    repair_verified_condition,
)

DATA_PATH = (
    Path(__file__).parents[3]
    / "src/solution_runner/pipelines/equations/verified_expression_transcriptions.json"
)
ENTRIES = json.loads(DATA_PATH.read_text())["entries"]


def condition(context):
    return next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )


@pytest.mark.parametrize("entry", ENTRIES, ids=lambda e: e["source_problem_id"])
def test_exact_source_transcription_is_visible_immutable_and_independent_of_answer_and_solution(
    entry,
):
    case = next(c for c in CASES if c["task"] == entry["source_problem_id"])
    context = deepcopy(case["context"])
    original = deepcopy(context)
    prepared, change = repair_verified_condition(context)
    assert context == original and prepared is not context
    assert change["transformation_target_id"].startswith("section:condition")
    assert condition(prepared)["html"] == entry["after_html"]
    assert repair_verified_condition(prepared) == (prepared, None)
    for s in context["normalized_content"]["sections"]:
        if s["key"] == "answer":
            s["html"] = "<p>987654321</p>"
        if s["key"] == "solution":
            s["html"] = "<p>Не использовать для восстановления.</p>"
    assert plan(case, context).answer == plan(case, original).answer


@pytest.mark.parametrize("entry", ENTRIES, ids=lambda e: e["source_problem_id"])
def test_altered_or_augmented_conditions_have_no_transcription(entry):
    case = next(c for c in CASES if c["task"] == entry["source_problem_id"])
    for extra in ["<p>Удвойте ответ.</p>", " ", "<script>changeAnswer()</script>"]:
        context = deepcopy(case["context"])
        condition(context)["html"] += extra
        prepared, change = repair_verified_condition(context)
        assert prepared is context and change is None
    context = deepcopy(case["context"])
    condition(context)["html"] = entry["after_html"]
    assert repair_verified_condition(context) == (context, None)


def test_transcription_records_change_only_the_reviewed_formula_and_are_packaged():
    hashes = {e["condition_sha256"] for e in ENTRIES}
    assert len(hashes) == len(ENTRIES) == 16
    for e in ENTRIES:
        assert (
            hashlib.sha256(e["before_html"].encode()).hexdigest()
            == e["condition_sha256"]
        )
        assert hashlib.sha256(e["after_html"].encode()).hexdigest() not in hashes
        soup = BeautifulSoup(e["before_html"], "html.parser")
        soup.select_one("[data-inline-latex]")["data-inline-latex"] = e["transcription"]
        assert str(soup) == e["after_html"]
        assert e["source_url"].startswith("https://math-ege.sdamgia.ru/problem?id=")
        assert all(
            len(im["svg_sha256"]) == 64 and im["url"].endswith(".svg")
            for im in e["source_images"]
        )
    config = tomllib.loads((Path(__file__).parents[3] / "pyproject.toml").read_text())
    assert (
        DATA_PATH.name
        in config["tool"]["setuptools"]["package-data"][
            "solution_runner.pipelines.equations"
        ]
    )


def test_all_transcribed_values_follow_independent_exact_identities():
    a, b = sp.symbols("a b", nonzero=True, real=True)
    expressions = {
        "549338": sp.Integer(4) ** sp.Rational(1, 5)
        * sp.Integer(16) ** sp.Rational(9, 10),
        "65815": a**-1 * b / ((6 * a) ** 2 * b**4) * 36 / (a**-3 * b**-3),
        "77400": sp.Integer(7) ** (sp.Rational(1, 5) + 2 * sp.Rational(9, 10)),
        "26735": sp.sqrt(65**2 - 56**2),
        "26830": (8 - 6) + (10 - 8),
        "67617": (5 - 3) + (9 - 5),
        "67669": (3 - 2) + (4 - 3),
        "67619": (4 - 3) + (5 - 4),
        "68509": sp.log(32) / sp.log(sp.Rational(1, 2)),
        "68473": sp.log(125) / sp.log(sp.Rational(1, 5)),
        "68553": sp.log(400) / sp.log(20),
        "68583": sp.log(sp.Rational(1, 20)) / sp.log(20)
        + sp.log(8) / sp.log(sp.Rational(1, 2)),
        "26852": sp.log(49) / sp.log(7),
        "4351": sp.log(81) / sp.log(9),
        "68821": sp.log(27) / sp.log(3),
        "69207": sp.log(sp.Rational(4, 5)) / sp.log(sp.Rational(5, 4)),
    }
    for task, expression in expressions.items():
        case = next(c for c in CASES if c["task"] == task)
        assert parse_rational(
            plan(case, deepcopy(case["context"])).answer
        ) == sp.simplify(expression)
