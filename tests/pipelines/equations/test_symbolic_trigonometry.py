"""Sign branches, original domains and exact symbolic trigonometric relations."""

from copy import deepcopy
from itertools import product

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from test_category_8_source_samples import CASES, plan

from solution_runner.pipelines.core.numbers import parse_rational


def question(group, expression, relation=None, domain=None):
    case = next(c for c in CASES if c["group"] == group)
    context = deepcopy(case["context"])
    html = '<p>Найдите <span data-inline-latex="' + expression + '"></span>'
    if relation:
        html += ', если <span data-inline-latex="' + relation + '"></span>'
    if domain:
        html += ' и <span data-inline-latex="' + domain + '"></span>'
    html += ".</p>"
    next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )["html"] = html
    return case, context


@pytest.mark.parametrize(
    "s,c,domain",
    [
        (sp.Rational(3, 5), sp.Rational(4, 5), r"\alpha\in(0;\frac{\pi}{2})"),
        (sp.Rational(3, 5), -sp.Rational(4, 5), r"\alpha\in(\frac{\pi}{2};\pi)"),
        (-sp.Rational(3, 5), -sp.Rational(4, 5), r"\alpha\in(\pi;\frac{3\pi}{2})"),
        (-sp.Rational(3, 5), sp.Rational(4, 5), r"\alpha\in(\frac{3\pi}{2};2\pi)"),
    ],
)
def test_complementary_signs_are_derived_from_every_quadrant(s, c, domain):
    for query, given, expected in [
        (r"\cos\alpha", r"\sin\alpha=" + sp.latex(s), c),
        (r"\sin\alpha", r"\cos\alpha=" + sp.latex(c), s),
        (r"\tg\alpha", r"\sin\alpha=" + sp.latex(s), s / c),
    ]:
        case, context = question("26777", query, given, domain)
        assert parse_rational(plan(case, context).answer) == expected


@pytest.mark.parametrize(
    "function,value",
    tuple(
        product(["sin", "cos"], [sp.Rational(-4, 5), sp.Rational(0), sp.Rational(3, 5)])
    ),
)
def test_double_cosine_needs_no_undetermined_complementary_sign(function, value):
    case, context = question(
        "26779", r"7\cos2\alpha", chr(92) + function + r"\alpha=" + sp.latex(value)
    )
    expected = 7 * (1 - 2 * value**2 if function == "sin" else 2 * value**2 - 1)
    assert parse_rational(plan(case, context).answer) == expected


@pytest.mark.parametrize("q", [-4, -1, sp.Rational(1, 5), 2])
def test_periodic_tangent_and_reciprocal_shift_preserve_all_signs(q):
    for query, expected in [
        (r"\tg(\alpha+7\pi)", q),
        (r"\tg(\alpha+\frac{5\pi}{2})", -1 / sp.Rational(q)),
    ]:
        case, context = question("26786", query, r"\tg\alpha=" + sp.latex(q))
        assert parse_rational(plan(case, context).answer) == expected


@pytest.mark.parametrize(
    "query,relation,domain",
    [
        (r"\cos\alpha", r"\sin\alpha=\frac35", None),
        (r"\sin2\alpha", r"\cos\alpha=\frac35", None),
        (r"\tg\alpha", r"\sin\alpha=2", None),
        (r"\cos\alpha", r"\sin\alpha=\frac35", r"\alpha\in(\pi;\frac{3\pi}{2})"),
        (r"\tg(\alpha+\frac{\pi}{2})", r"\tg\alpha=0", None),
        (r"\frac{\sin2\alpha}{\cos\alpha}", r"\sin\alpha=1", None),
        (r"\frac{0\sin2\alpha}{\cos\alpha}", r"\sin\alpha=1", None),
        (r"\cos\beta", r"\sin\alpha=\frac35", None),
    ],
)
def test_ambiguous_signs_inconsistent_conditions_and_original_poles_fail_closed(
    query, relation, domain
):
    # Use braced fractions exactly as source markup does.
    relation = relation.replace(r"\frac35", r"\frac{3}{5}")
    case, context = question("26777", query, relation, domain)
    with pytest.raises(ValueError):
        plan(case, context)


@pytest.mark.parametrize(
    "given,expected", [(r"\sin\alpha=0", 0), (r"\sin\alpha=-1", -1)]
)
def test_axes_inside_a_broad_interval_are_handled_without_inventing_a_quadrant(
    given, expected
):
    case, context = question("26777", r"\sin\alpha", given, r"-\pi\lt\alpha\lt\pi")
    assert parse_rational(plan(case, context).answer) == expected


@pytest.mark.parametrize("a,b,r", [(5, 13, 6), (2, 7, 3), (-3, 5, 1), (8, 2, 5)])
def test_squared_function_relation_uses_both_independently_equivalent_methods(a, b, r):
    case, context = question(
        "26787", r"\tg^2\alpha", rf"{a}\sin^2\alpha+({b})\cos^2\alpha={r}"
    )
    s2 = sp.Rational(r - b, a - b)
    c2 = 1 - s2
    assert parse_rational(plan(case, context).answer) == s2 / c2
    html = next(
        t["value"]["html"]
        for t in plan(case, context).transformations
        if t["transformation_target_id"].startswith("section:solution")
    )
    assert html.index("Первый способ") < html.index("Второй способ")


@pytest.mark.parametrize(
    "relation",
    [
        r"\sin^2\alpha+\cos^2\alpha=1",
        r"\sin^2\alpha+2\cos^2\alpha=1",
        r"\sin^2\alpha+2\cos^2\alpha=3",
    ],
)
def test_squared_relation_cannot_select_an_arbitrary_tangent_or_ignore_its_pole(
    relation,
):
    case, context = question("26787", r"\tg^2\alpha", relation)
    with pytest.raises(ValueError):
        plan(case, context)


@pytest.mark.parametrize(
    "a,b,c,d,t", [(2, 3, 1, -4, 5), (1, -2, 3, 1, -1), (5, 1, -2, 4, sp.Rational(1, 2))]
)
def test_affine_ratio_equation_recovers_the_independently_chosen_tangent(a, b, c, d, t):
    expected = sp.cancel((a * t + b) / (c * t + d))
    relation = rf"\frac{{{a}\sin\alpha+({b})\cos\alpha}}{{{c}\sin\alpha+({d})\cos\alpha}}={sp.latex(expected)}"
    case, context = question("26790", r"\tg\alpha", relation)
    assert parse_rational(plan(case, context).answer) == t


@pytest.mark.parametrize(
    "relation",
    [
        r"\frac{\sin\alpha}{\cos\alpha}=0",
        r"\frac{2\sin\alpha+2\cos\alpha}{\sin\alpha+\cos\alpha}=3",
    ],
)
def test_zero_tangent_is_valid_but_a_spurious_cross_multiplied_solution_is_not(
    relation,
):
    case, context = question("26791", r"\tg\alpha", relation)
    if relation.endswith("=0"):
        assert plan(case, context).answer == "0"
    else:
        with pytest.raises(ValueError):
            plan(case, context)


@pytest.mark.parametrize("group", ["26788", "26789"])
def test_both_ratio_methods_keep_the_tangent_substitution(group):
    case = next(c for c in CASES if c["task"] == group)
    html = next(
        t["value"]["html"]
        for t in plan(case, deepcopy(case["context"])).transformations
        if t["transformation_target_id"].startswith("section:solution")
    )
    assert html.index("Первый способ") < html.index("Второй способ")
    assert any(
        r"\tg(" in t["data-inline-latex"]
        for t in BeautifulSoup(html, "html.parser").select("[data-inline-latex]")
    )


def test_generated_numeric_and_symbolic_equalities_hold_on_all_admissible_branches():
    import json
    import re
    from pathlib import Path

    from solution_runner.pipelines.equations.trig_angles import C, S, multiple_angle
    from solution_runner.pipelines.equations.trig_given import calculate
    from solution_runner.pipelines.equations.trig_given_domain import candidates
    from solution_runner.pipelines.equations.trig_relation import _read
    from solution_runner.pipelines.equations.trig_symbolic_parser import (
        SymbolicTrigonometricParser,
        compile_atoms,
    )

    groups = {
        g["key"]: g["rule"]
        for g in json.loads(
            (Path(__file__).parent / "fixtures/category_8.json").read_text()
        )["groups"]
        if g["rule"].startswith("trigonometric-")
    }
    checked = 0
    for case in CASES:
        if case["group"] not in groups:
            continue
        rule = groups[case["group"]]
        result = plan(case, deepcopy(case["context"]))
        if "equation" in rule or "square-relation" in rule:
            square = "square-relation" in rule
            _question, expression, r, denominators, variable = _read(
                case["context"], 2 if square else 1
            )
            value = sp.Rational(parse_rational(result.answer))
            tangent = sp.sqrt(value) if square else value
            pairs = candidates("tg", tangent, None)
            if square:
                pairs += candidates("tg", -tangent, None)
            pairs = [
                pair
                for pair in pairs
                if all(
                    sp.simplify(d.subs({S: pair[0], C: pair[1]})).is_zero is False
                    for d in denominators
                )
            ]
            assert pairs
            assert all(
                sp.simplify(expression.subs({S: s, C: c}) - r) == 0 for s, c in pairs
            )
            base = 1
        else:
            calc = calculate(case["context"])
            base, variable, _, _ = compile_atoms(calc.parser)
            pairs = calc.pairs or [
                (sp.Rational(3, 5), sp.Rational(4, 5)),
                (-sp.Rational(3, 5), sp.Rational(4, 5)),
            ]
        html = next(
            t["value"]["html"]
            for t in result.transformations
            if t["transformation_target_id"].startswith("section:solution")
        )
        for tag in BeautifulSoup(html, "html.parser").select("[data-inline-latex]"):
            text = tag["data-inline-latex"]
            if "=" not in text or any(
                token in text
                for token in [r"\quad", r"\ne", r"\Longrightarrow", "<", ">"]
            ):
                continue
            if re.search(r"[a-zA-Z]", re.sub(r"\\[a-zA-Z]+", "", text)):
                continue
            atoms = {}
            pieces = [
                re.sub(r"\\frac(\d)(?=\{)", r"\\frac{\1}", part)
                for part in text.split("=")
            ]
            try:
                nodes = [
                    SymbolicTrigonometricParser(part, atoms).parse() for part in pieces
                ]
            except ValueError as exc:
                raise AssertionError((case["task"], text)) from exc
            bindings = {
                symbol: multiple_angle(
                    atom.function, atom.coefficient // base, int(2 * atom.shift)
                )
                for symbol, atom in atoms.items()
            }
            assert all(
                atom.variable == variable and atom.coefficient % base == 0
                for atom in atoms.values()
            )
            for s, c in pairs:
                values = [
                    sp.simplify(node.value.xreplace(bindings).subs({S: s, C: c}))
                    for node in nodes
                ]
                assert all(sp.simplify(v - values[0]) == 0 for v in values[1:]), (
                    case["task"],
                    text,
                    values,
                )
            checked += 1
    assert checked > 300
