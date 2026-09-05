"""Verify exact inference for right triangles split by altitude CH."""

from __future__ import annotations

import pytest

from solution_runner.pipelines.grid_polygon.right_triangle_pipeline.altitude_solver import (
    AltitudeSolveError,
    solve_altitude_condition,
)


def _condition(*formulas: str, request: str, plain: str = "") -> str:
    """Build one schema-v3 condition fragment with explicit altitude geometry."""

    spans = ", ".join(
        f'<span data-inline-latex="{formula}"></span>' for formula in formulas
    )
    return (
        '<p>В треугольнике ABC угол C равен 90°, CH — высота, '
        + plain
        + spans
        + f'. Найдите {request}.</p>'
    )


@pytest.mark.parametrize(
    ("condition_html", "requested", "answer"),
    [
        (_condition(r"\tg A=\frac{1}{5}", request="AH", plain="AB = 13, "), "AH", "12,5"),
        (_condition(r"AB=13", r"\tg A=5", request="BH"), "BH", "12,5"),
        (_condition(r"AB=13", r"\tg A=\frac{1}{5}", request="CH"), "CH", "2,5"),
        (_condition(r"BC=3", r"\sin A=\frac{1}{6}", request="AH"), "AH", "17,5"),
        (_condition(r"BC=8", r"\sin A=0{,}5", request="BH"), "BH", "4"),
        (_condition(r"BC=5", r"\sin A=\frac{7}{25}", request="CH"), "CH", "4,8"),
        (_condition(r"BC=3", r"\cos A=\frac{\sqrt{35}}{6}", request="AH"), "AH", "17,5"),
        (_condition(r"BC=5", r"\cos A=\frac{7}{25}", request="BH"), "BH", "4,8"),
        (_condition(r"BC=8", r"\cos A=0{,}5", request="CH"), "CH", "4"),
        (_condition(r"BC=8", r"BH=4", request=r"\sin A"), "sinA", "0,5"),
        (_condition(r"BC=25", r"BH=20", request=r"\cos A"), "cosA", "0,6"),
        (_condition(r"BC=4\sqrt{5}", r"BH=4", request=r"\tg A"), "tgA", "0,5"),
        (_condition(r"CH=20", r"BC=25", request=r"\sin A"), "sinA", "0,6"),
        (_condition(r"CH=4", r"BC=8", request=r"\cos A"), "cosA", "0,5"),
        (_condition(r"CH=4", r"BC=\sqrt{17}", request=r"\tg A"), "tgA", "0,25"),
        (_condition(r"CH=24", r"BH=7", request=r"\sin A"), "sinA", "0,28"),
        (_condition(r"CH=7", r"BH=24", request=r"\cos A"), "cosA", "0,28"),
        (_condition(r"CH=8", r"BH=4", request=r"\tg A"), "tgA", "0,5"),
        (_condition(r"AH=27", r"\tg A=\frac{2}{3}", request="BH"), "BH", "12"),
        (_condition(r"BH=12", r"\tg A=\frac{2}{3}", request="AH"), "AH", "27"),
        (_condition(r"BH=12", r"\sin A=\frac{2}{3}", request="AB"), "AB", "27"),
        (_condition(r"AH=12", r"\cos A=\frac{2}{3}", request="AB"), "AB", "27"),
    ],
)
def test_solver_covers_audited_direct_and_multi_step_combinations(
    condition_html: str,
    requested: str,
    answer: str,
) -> None:
    """Compute every audited parent shape without selecting by group number."""

    solution = solve_altitude_condition(condition_html)

    assert solution.requested == requested
    assert solution.answer == answer
    assert solution.rows


def test_tangent_with_hypotenuse_is_rendered_through_pythagoras() -> None:
    """Do not disguise the tangent/hypotenuse derivation as a trig identity."""

    solution = solve_altitude_condition(
        _condition(r"AB=13", r"\tg A=\frac{1}{5}", request="AH")
    )

    joined = " ".join(solution.rows)
    assert r"AB^2=AC^2+BC^2" in joined
    assert r"1+\tg^2" not in joined
    assert r"\frac{1}{\cos^2" not in joined


def test_given_tangent_introduces_proportional_sides_before_pythagoras() -> None:
    """Render the approved value–coefficients–sides equivalence in that order."""

    solution = solve_altitude_condition(
        _condition(r"AB=10", r"\tg A=3", request="AH")
    )

    assert solution.rows[:4] == (
        r"\tg A=3=\frac{3x}{x}=\frac{BC}{AC}\Longrightarrow BC=3x,\ AC=x",
        r"AB^2=AC^2+BC^2",
        r"10^2=x^2+(3x)^2\Longrightarrow x=\sqrt{10}",
        r"AC=x=\sqrt{10}",
    )
    assert solution.rows[4] == (
        r"\tg A=3=\frac{3y}{y}=\frac{CH}{AH}"
        r"\Longrightarrow CH=3y,\ AH=y"
    )
    assert solution.rows[6] == (
        r"(\sqrt{10})^2=y^2+(3y)^2\Longrightarrow y=1"
    )


def test_fractional_tangent_keeps_side_value_distinct_from_scale() -> None:
    """Do not report the adjacent side coefficient times x as x itself."""

    solution = solve_altitude_condition(
        _condition(r"AB=10", r"\tg A=\frac{1}{3}", request="BH")
    )

    assert solution.rows[:4] == (
        r"\tg A=\frac{1}{3}=\frac{x}{3x}=\frac{BC}{AC}"
        r"\Longrightarrow BC=x,\ AC=3x",
        r"AB^2=AC^2+BC^2",
        r"10^2=(3x)^2+x^2\Longrightarrow x=\sqrt{10}",
        r"AC=3x=3\sqrt{10}",
    )
    assert solution.answer == "1"
    assert r"AH=9=3y\Longrightarrow y=3" not in solution.rows
    assert r"AH=3y=9" in solution.rows
    assert solution.rows[-1] == r"BH=AB-AH=10-9=1"


def test_requested_bh_uses_hypotenuse_segment_subtraction() -> None:
    """Prefer BH = AB - AH once both hypotenuse segments are known."""

    solution = solve_altitude_condition(
        _condition(r"AB=87", r"\tg A=\frac{2}{5}", request="BH")
    )

    assert solution.answer == "12"
    assert solution.rows[-1] == r"BH=AB-AH=87-75=12"
    assert all(r"\frac{BH}{CH}" not in row for row in solution.rows)


def test_requested_bh_does_not_use_circular_subtraction() -> None:
    """Keep the direct small-triangle path when AB itself depends on BH."""

    solution = solve_altitude_condition(
        _condition(r"AH=15", r"\tg A=\frac{3}{5}", request="BH")
    )

    assert solution.answer == "5,4"
    assert r"AB=AH+BH" not in " ".join(solution.rows)
    assert solution.rows[-1] == (
        r"\tg A=\frac{BH}{CH}\Longrightarrow "
        r"BH=CH\tg A=9\cdot\frac{3}{5}=\frac{27}{5}"
    )


def test_given_sine_uses_the_same_proportional_side_style() -> None:
    """Apply the proportional-side rendering to sine, not only tangent."""

    solution = solve_altitude_condition(
        _condition(r"BC=3", r"\sin A=\frac{1}{6}", request="AH")
    )

    assert solution.rows[:3] == (
        r"\sin A=\frac{1}{6}=\frac{x}{6x}=\frac{BC}{AB}"
        r"\Longrightarrow BC=x,\ AB=6x",
        r"BC=3=x\Longrightarrow x=3",
        r"AB=6x=18",
    )


def test_solver_uses_basic_identity_only_between_sine_and_cosine() -> None:
    """Use the complementary-function transition only when it is the goal."""

    solution = solve_altitude_condition(
        _condition(r"\sin A=\frac{7}{25}", request=r"\cos A")
    )

    assert any(r"\cos A=\sqrt{1-(\sin A)^2}" in row for row in solution.rows)


def test_given_cosine_reaches_ah_without_deriving_sine() -> None:
    """Prefer the given cosine and Pythagoras over a complementary function."""

    solution = solve_altitude_condition(
        _condition(r"BC=7", r"\cos A=\frac{2\sqrt{6}}{7}", request="AH")
    )

    assert solution.answer == "4,8"
    assert solution.rows == (
        r"\cos A=\frac{2\sqrt{6}}{7}=\frac{2\sqrt{6}x}{7x}=\frac{AC}{AB}"
        r"\Longrightarrow AC=2\sqrt{6}x,\ AB=7x",
        r"AB^2=AC^2+BC^2",
        r"(7x)^2=(2\sqrt{6}x)^2+7^2\Longrightarrow x=\frac{7}{5}",
        r"AC=2\sqrt{6}x=\frac{14\sqrt{6}}{5}",
        r"\cos A=\frac{AH}{AC}\Longrightarrow "
        r"AH=AC\cos A=\frac{14\sqrt{6}}{5}\cdot\frac{2\sqrt{6}}{7}="
        r"\frac{24}{5}",
    )
    assert all(r"\sin A" not in row for row in solution.rows)


def test_solver_rejects_an_underdetermined_unknown_variant() -> None:
    """Fail closed when the requested quantity cannot be inferred uniquely."""

    with pytest.raises(AltitudeSolveError, match="cannot derive AH"):
        solve_altitude_condition(_condition(r"AB=13", request="AH"))


def test_solver_rejects_redundant_inconsistent_data() -> None:
    """Compare every redundant condition value against exact inference."""

    with pytest.raises(AltitudeSolveError, match="inconsistent BC"):
        solve_altitude_condition(
            _condition(r"AB=5", r"AC=4", r"BC=4", request=r"\sin A")
        )


def test_solver_requires_the_altitude_declaration() -> None:
    """Do not interpret H quantities without the declared construction."""

    condition = (
        '<p>В треугольнике ABC угол C равен 90°, '
        '<span data-inline-latex="CH=4"></span>, '
        '<span data-inline-latex="BH=3"></span>. Найдите BC.</p>'
    )

    with pytest.raises(AltitudeSolveError, match="must declare CH as the altitude"):
        solve_altitude_condition(condition)


def test_solver_normalizes_cyrillic_geometry_labels_from_source_html() -> None:
    """Accept visually identical italic Cyrillic labels without changing prose."""

    condition = (
        '<p>В треугольнике <i>АВС</i> угол <i>С</i> равен 90°, '
        '<i>СН</i> — высота, <span data-inline-latex="AB=13"></span>, '
        '<span data-inline-latex="\\tg A=5"></span>. Найдите <i>ВН</i>.</p>'
    )

    solution = solve_altitude_condition(condition)

    assert solution.requested == "BH"
    assert solution.answer == "12,5"


def test_solver_recognizes_height_request_without_separate_declaration() -> None:
    """Treat «найдите высоту CH» as both construction and request."""

    condition = (
        '<p>В треугольнике ABC угол C равен 90°, '
        '<span data-inline-latex="AB=13"></span>, '
        '<span data-inline-latex="\\tg A=\\frac{1}{5}"></span>. '
        'Найдите высоту CH.</p>'
    )

    solution = solve_altitude_condition(condition)

    assert solution.requested == "CH"
    assert solution.answer == "2,5"


def test_solver_reads_plain_height_and_side_values() -> None:
    """Parse values split between source text and semantic variable tags."""

    condition = (
        '<p>В треугольнике ABC угол C равен 90°, высота '
        '<var data-math-identifier="CH">CH</var> равна 20, '
        '<var data-math-identifier="BC">BC</var> = 25. Найдите '
        '<span data-inline-latex="\\sin A"></span>.</p>'
    )

    solution = solve_altitude_condition(condition)

    assert solution.requested == "sinA"
    assert solution.answer == "0,6"


def test_solver_reads_semantic_height_value_from_following_formula_span() -> None:
    """Associate a semantic side label with its adjacent value-only formula."""

    condition = (
        '<p>В треугольнике <var data-math-identifier="ABC">ABC</var> угол '
        '<var data-math-identifier="C">C</var> равен 90°, высота '
        '<var data-math-identifier="CH">CH</var> равна '
        '<span data-inline-latex="20"></span>, '
        '<span data-inline-latex="BH=15"></span>. Найдите '
        '<span data-inline-latex="\\sin A"></span>.</p>'
    )

    solution = solve_altitude_condition(condition)

    assert solution.requested == "sinA"
    assert solution.answer == "0,6"
    assert r"BC=\sqrt{BH^2+CH^2}" in " ".join(solution.rows)


def test_solver_supports_requested_trigonometric_function_of_angle_b() -> None:
    """Derive a requested function of B from the corresponding small triangle."""

    condition = _condition(r"AC=25", r"AH=15", request=r"\cos B")

    solution = solve_altitude_condition(condition)

    assert solution.requested == "cosB"
    assert solution.answer == "0,8"
    assert solution.rows == (
        r"CH=\sqrt{AC^2-AH^2}=\sqrt{(25)^2-(15)^2}=20",
        r"\cos B=\frac{CH}{AC}=\frac{20}{25}=\frac{4}{5}",
    )


def test_solver_reads_length_request_from_source_prose() -> None:
    """Recognize «найдите длину отрезка» around a semantic variable label."""

    condition = (
        '<p>В треугольнике <var data-math-identifier="ABC">ABC</var> угол '
        '<var data-math-identifier="C">C</var> равен 90°, '
        '<var data-math-identifier="CH">CH</var> — высота, '
        '<var data-math-identifier="BC">BC</var> = 5 и '
        '<span data-inline-latex="\\cos A=\\frac{2\\sqrt{6}}{5}"></span>. '
        'Найдите длину отрезка <var data-math-identifier="AH">AH</var>.</p>'
    )

    solution = solve_altitude_condition(condition)

    assert solution.requested == "AH"
    assert solution.answer == "24"


def test_solver_reads_combined_formula_cell() -> None:
    """Parse angle and side equalities joined by source ``\\quad`` separators."""

    condition = (
        '<p>В треугольнике <span data-inline-latex="ABC"></span>: '
        '<span data-inline-latex="\\angle C=90^{\\circ},\\quad BC=2,'
        '\\quad AC=2\\sqrt{3}"></span>. Найдите '
        '<span data-inline-latex="\\cos B"></span>.</p>'
    )

    solution = solve_altitude_condition(condition)

    assert solution.requested == "cosB"
    assert solution.answer == "0,5"


def test_solver_reads_value_after_dangling_equality_in_formula_cell() -> None:
    """Join a formula-cell side label with its adjacent visible numeric value."""

    condition = (
        '<p>В треугольнике <var data-math-identifier="ABC">ABC</var> угол '
        '<var data-math-identifier="C">C</var> равен '
        '<span data-inline-latex="90^\\circ,\\quad \\sin A=\\frac{3}{5},'
        '\\quad BC="></span>3, <var data-math-identifier="CH">CH</var> — '
        'высота. Найдите <span data-inline-latex="BH"></span>.</p>'
    )

    solution = solve_altitude_condition(condition)

    assert solution.requested == "BH"
    assert solution.answer == "1,8"


def test_solver_accepts_requested_ch_as_the_implicit_altitude() -> None:
    """Support source tasks that name no other H-segment and ask for CH."""

    condition = _condition(
        r"BC=8",
        r"\cos A=0{,}5",
        request="CH",
    ).replace("CH — высота, ", "")

    solution = solve_altitude_condition(condition)

    assert solution.answer == "4"
