"""Exact high-angle certificates, dyadic partitions and preserved integer notation."""

from types import SimpleNamespace

import pytest
import sympy as sp

from solution_runner.pipelines.equations.exam_trigonometric import analyze, select
from solution_runner.pipelines.equations.exam_trigonometric_angle_domain import (
    equivalent,
    series,
)
from solution_runner.pipelines.equations.exam_trigonometric_angle_product import (
    compile_product,
)
from solution_runner.pipelines.equations.exam_trigonometric_compile import C, S
from solution_runner.pipelines.equations.exam_trigonometric_ratio_product import (
    compile_product as compile_equal,
)
from solution_runner.pipelines.equations.exam_trigonometric_square_difference import (
    parameter,
)
from solution_runner.pipelines.equations.exam_trigonometric_variants import (
    root_notation,
)
from solution_runner.pipelines.word_problems.common import UnsupportedCondition

X = sp.Symbol("x", real=True)
FORMULA = r"\frac{\cos 2x\cdot\cos 8x-\cos 10x}{\cos x+1}=0"
PARENT = r'<p><span data-inline-latex="AB=A"></span>расщепляется</p><p><span data-inline-latex="\tg x\sin^2 x=\tg x"></span></p><p><span data-inline-latex="\tg x=0"></span>Отберем корни, решая двойное неравенство.</p>'


@pytest.mark.parametrize(
    "level,expected",
    [(0, "0 1"), (1, "0 1"), (sp.Rational(1, 4), "0 1/6 5/6 1 7/6 11/6"), (2, "0 1")],
)
def test_product_split_keeps_tangent_zero_without_assuming_sine_values_are_valid(
    level, expected
):
    f = r"\tg x\cdot\sin^2 x=" + sp.latex(level) + r"\tg x"
    a = analyze(f, r"[0;2\pi]", (sp.S.Zero, 2 * sp.pi, True, True), PARENT)
    assert a.ratio_product.method == "split_equal" and a.poles == (C,)
    assert select(a.series, (0, 2, True, False))[0] == tuple(
        map(sp.Rational, expected.split())
    )


@pytest.mark.parametrize(
    "formula",
    [
        r"\tg x\sin^2(2x)=\tg x",
        r"\ctg x\sin^2 x=\ctg x",
        r"\tg x\sin^2 x=5\tg x",
        r"\tg x\sin^2 x=-\tg x",
        r"\tg(x+\pi/2)\sin^2 x=\tg(x+\pi/2)",
        r"\tg x\sin^2 x=\tg x+1",
    ],
)
def test_unreviewed_equal_product_shapes_fail_closed(formula):
    with pytest.raises(UnsupportedCondition):
        compile_equal(formula, "split_equal")


def test_high_angle_identity_is_proved_by_exact_unit_circle_remainder():
    raw = sp.cos(2 * X) * sp.cos(8 * X) - sp.cos(10 * X)
    factored = sp.sin(2 * X) * sp.sin(8 * X)
    assert equivalent(raw, factored)
    assert not equivalent(raw, factored + 1)
    assert not equivalent(raw, sp.sin(3 * X) * sp.sin(8 * X))
    assert not equivalent(raw, sp.Symbol("y"))


@pytest.mark.parametrize(
    "denominator", [r"\cos(2x)+1", r"\cos^3 x+1", r"\cos x+1+\sin(2x)"]
)
def test_angle_fraction_preserves_only_bounded_original_base_angle_poles(denominator):
    with pytest.raises(UnsupportedCondition):
        compile_product(FORMULA.replace(r"\cos x+1", denominator))


def test_scalar_multiple_of_original_pole_has_the_same_nested_lattice():
    equation = compile_product(FORMULA.replace(r"\cos x+1", r"2\cos x+2"))
    assert equation.angle_product.nested and equation.poles == (2 * C + 2,)
    residues = tuple(sp.Rational(k, 8) for k in range(16) if k != 8)
    result = series(equation.angle_product, residues)
    assert len(result) == 4 and select(result, (0, 2, True, False))[0] == residues
    for bad in (residues + (sp.S.One,), residues[1:]):
        with pytest.raises(UnsupportedCondition, match="complete lattice"):
            series(equation.angle_product, bad)


@pytest.mark.parametrize(
    "html,expected",
    [
        (
            r'<span data-inline-latex="x=\arcsin(\frac{3}{5})+2\pi k, k\in\mathbb{Z}"></span>',
            "k",
        ),
        (
            r'<span data-inline-latex="\begin{aligned}x&amp;=\pi n\\x&amp;=\frac{\pi}{3}+2\pi n\end{aligned}, n\in\mathbb{Z}"></span>',
            "n",
        ),
        (
            r'<span data-inline-latex="x=2\pi k"></span><span data-inline-latex="x=2\pi n"></span>',
            "k",
        ),
    ],
)
def test_parameter_comes_from_root_families_including_aligned_markup(html, expected):
    assert parameter(html) == expected


def test_notation_rename_leaves_asset_keys_and_other_identifiers_untouched():
    text = r'<img data-asset-key="image_1" src="/assets/preview-k"/><span data-inline-latex="x=\pi k,\quad k\in\mathbb Z"></span>'
    renamed = root_notation(SimpleNamespace(parameter="n"), (text,))[0]
    assert "/assets/preview-k" in renamed and 'data-asset-key="image_1"' in renamed
    assert r"x=\pi n,\quad n\in\mathbb Z" in renamed
    assert root_notation(SimpleNamespace(parameter="k"), (text,)) == (text,)


def test_affine_cosine_factors_with_a_base_sine_pole_have_the_complete_exact_roots():
    from solution_runner.pipelines.equations.exam_trigonometric_angle_product import (
        branches,
    )
    from solution_runner.pipelines.equations.exam_trigonometric_domain import (
        without_poles,
    )

    equation = compile_product(r"\frac{\cos 3x+\cos 7x}{\sin x}=0")
    assert equation.poles == (S,)
    retained = without_poles(branches(equation.angle_product), equation.poles)
    actual = {q for branch in retained for q in branch.residues}
    expected = {sp.Rational(2 * k + 1, 10) for k in range(10)} | {
        sp.Rational(1, 4),
        sp.Rational(3, 4),
        sp.Rational(5, 4),
        sp.Rational(7, 4),
    }
    assert actual == expected and len(actual) == 14
    for q in actual:
        angle = q * sp.pi
        assert (
            sp.sin(angle) != 0
            and sp.simplify((sp.cos(3 * angle) + sp.cos(7 * angle)) / sp.sin(angle))
            == 0
        )
    assert equivalent(sp.cos(3 * X) + sp.cos(7 * X), 2 * sp.cos(2 * X) * sp.cos(5 * X))


def test_large_unreviewed_product_does_not_expand_into_exponentially_many_angle_sums():
    formula = r"\cdot".join(r"\sin(" + str(k) + "x)" for k in range(1, 13)) + "=0"
    with pytest.raises(UnsupportedCondition, match="exactly two"):
        compile_product(formula)
