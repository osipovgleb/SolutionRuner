import pytest

from solution_runner.pipelines.equations.group_26656 import (
    UnsupportedCondition,
    build_context_repair_plan,
    build_repair_plan,
)


@pytest.mark.parametrize(
    ("formula", "answer"),
    [
        (r"\sqrt{15-2x}=3", "3"),
        (r"\sqrt{30-7x}=4", "2"),
        (r"\sqrt{-32-x}=2", "-36"),
        (r"\sqrt{59-x}=8", "-5"),
        (r"\sqrt{-\frac{1}{2}+\frac{3}{2}x}=\frac{1}{2}", "0,5"),
        (r"\sqrt{1+2x}=\frac{1}{2}", "-0,375"),
        (r"\sqrt{x+3}=3", "6"),
        (r"\sqrt{4x+32}=8", "8"),
        (r"\sqrt{9x-47}=4", "7"),
        (r"\sqrt{-4x}=2", "-1"),
    ],
)
def test_computes_signed_rational_affine_equations_exactly(formula: str, answer: str) -> None:
    plan = build_repair_plan(formula)
    assert plan.answer == answer
    assert formula in plan.solution_html


@pytest.mark.parametrize("formula", [r"\sqrt{1-0x}=1", r"\sqrt{1-2x}=-1", r"\sqrt{x+2x}=1"])
def test_unknown_or_invalid_forms_fail_closed(formula: str) -> None:
    with pytest.raises(UnsupportedCondition):
        build_repair_plan(formula)


def _context(formula: str, *, answer: str = "", solution: str = "") -> dict:
    sections = [
        {
            "key": "condition",
            "section_id": "condition:1",
            "transformation_target_id": "section:condition:1",
            "asset_keys": [],
            "html": f'<p>Най­ди­те ко­рень урав­не­ния <span data-inline-latex="{formula}"></span>.</p>',
        }
    ]
    if answer:
        sections.append(
            {
                "key": "answer",
                "section_id": "answer:1",
                "transformation_target_id": "section:answer:1",
                "asset_keys": [],
                "html": f'<p><span data-effect="spaced">{answer}</span></p>',
            }
        )
    if solution:
        sections.append(
            {
                "key": "solution",
                "section_id": "solution:1",
                "transformation_target_id": "section:solution:1",
                "asset_keys": [],
                "html": solution,
            }
        )
    return {
        "normalized_content": {
            "format": "teacherhelper-normalized",
            "schema_version": 3,
            "assets": [],
            "sections": sections,
        }
    }


def test_context_plan_repairs_and_then_converges() -> None:
    context = _context(r"\sqrt{30-7x}=4", answer="999")
    plan = build_context_repair_plan(context)
    assert plan.answer == "2"
    assert {item["transformation_target_id"] for item in plan.transformations} == {
        "section:solution",
        "section:answer:1",
    }

    context["normalized_content"]["sections"][-1]["html"] = (
        '<p><span data-effect="spaced">2</span></p>'
    )
    context["normalized_content"]["sections"].append(
        {
            "key": "solution",
            "section_id": "solution:1",
            "transformation_target_id": "section:solution:1",
            "asset_keys": [],
            "html": plan.solution_html,
        }
    )
    assert build_context_repair_plan(context).transformations == ()


def test_context_accepts_the_observed_colon_variant() -> None:
    context = _context(r"\sqrt{59-x}=8", answer="-5")
    context["normalized_content"]["sections"][0]["html"] = (
        '<p>Най­ди­те ко­рень урав­не­ния: <span data-inline-latex="\\sqrt{59-x}=8"></span>.</p>'
    )
    assert build_context_repair_plan(context).answer == "-5"


def test_context_delegates_the_observed_html_exponential_equation() -> None:
    context = {
        "normalized_content": {
            "format": "teacherhelper-normalized",
            "schema_version": 3,
            "assets": [],
            "sections": [
                {
                    "key": "condition",
                    "section_id": "condition:1",
                    "transformation_target_id": "section:condition:1",
                    "asset_keys": [],
                    "html": "<p>Най­ди­те ко­рень урав­не­ния 5<sup>2 + <i>x</i></sup> = 125<sup><i>x</i></sup>.</p>",
                },
                {
                    "key": "answer",
                    "section_id": "answer:1",
                    "transformation_target_id": "section:answer:1",
                    "asset_keys": [],
                    "html": '<p><span data-effect="spaced">1</span></p>',
                },
            ],
        }
    }

    plan = build_context_repair_plan(context)

    assert plan.answer == "1"
    assert {item["transformation_target_id"] for item in plan.transformations} == {
        "section:solution"
    }


@pytest.mark.parametrize(
    ("formula", "condition_html", "answer"),
    [
        (r"\sqrt{8-x}=5", '<p>Ре­ши­те урав­не­ние <span data-inline-latex="\\sqrt{8-x}=5"></span>.</p>', "-17"),
        (r"\sqrt{5x-1}=7", '<p>Най­ди­те ко­рень урав­не­ния <span data-inline-latex="\\sqrt{5x-1}=7"></span></p>', "10"),
    ],
)
def test_context_accepts_observed_wording_and_terminal_punctuation_variants(
    formula: str, condition_html: str, answer: str,
) -> None:
    context = _context(formula)
    context["normalized_content"]["sections"][0]["html"] = condition_html

    assert build_context_repair_plan(context).answer == answer


def test_context_reflows_formula_outside_the_introductory_paragraph() -> None:
    context = _context(r"\sqrt{39-2x}=5", answer="-7")
    context["normalized_content"]["sections"][0]["html"] = (
        '<p>Най­ди­те ко­рень урав­не­ния: </p> '
        '<span data-inline-latex="\\sqrt{39-2x}=5"></span>.'
    )

    plan = build_context_repair_plan(context)

    assert plan.answer == "7"
    assert plan.transformations[0] == {
        "transformation_target_id": "section:condition:1",
        "operation": "rewrite",
        "value": {
            "title": "Условие",
            "html": '<p>Най­ди­те ко­рень урав­не­ния <span data-inline-latex="\\sqrt{39-2x}=5"></span>.</p>',
            "asset_keys": [],
        },
    }
