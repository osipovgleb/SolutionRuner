from solution_runner.pipelines.equations.group_trigonometric import (
    _ASSETS,
    build_context_repair_plan,
    build_repair_plan,
    required_assets,
)


def _context(formula: str, wording: str) -> dict:
    return {
        "normalized_content": {
            "format": "teacherhelper-normalized", "schema_version": 3,
            "assets": [{"asset_key": "image_1", "asset_id": "problem-local-asset"}],
            "sections": [
                {"key": "condition", "transformation_target_id": "section:condition:1", "html": f'<p>{wording} <span data-inline-latex="{formula}"></span>.</p>'},
                {"key": "solution", "transformation_target_id": "section:solution:1", "html": ""},
                {"key": "answer", "transformation_target_id": "section:answer:1", "html": ""},
            ],
        }
    }


def test_all_standard_values_have_uploaded_assets() -> None:
    assert len(_ASSETS) == 25


def test_cosine_parent_selects_largest_negative_root_and_reuses_local_asset() -> None:
    formula = r"\cos\frac{\pi(x-7)}{3}=\frac{1}{2}"
    context = _context(formula, "Найдите наибольший отрицательный корень уравнения")
    context["normalized_content"]["assets"] = [{
        "asset_key": "shared_26b67b3a5d0d4a43", "asset_id": _ASSETS["cos-half.svg"],
    }]
    plan = build_context_repair_plan(context)
    assert plan.answer == "-4"
    assert r"\cos\,u" not in plan.solution_html
    assert r"\left[\begin{aligned}" in plan.solution_html
    assert r"\frac{\pi}{3}" in plan.solution_html
    assert r"\pi(x-7)=\pi+6\pi k" in plan.solution_html
    assert r"x-7=1+6k" in plan.solution_html
    assert 'data-formula-render-mode="display"' in plan.solution_html
    assert r"\cos \frac{\pi(x-7)}{3}=\frac{1}{2}\iff " in plan.solution_html
    assert '<center><p><span data-formula-render-mode="display"' in plan.solution_html
    assert r"\iff \left[\begin{aligned}x-7=1+6k" in plan.solution_html
    assert "x=8+6k" in plan.solution_html
    assert "x=6+6k" in plan.solution_html
    assert "<table>" in plan.solution_html
    assert 'data-inline-latex="k=-2"' in plan.solution_html
    assert "Первый корень" in plan.solution_html
    assert "Второй корень" in plan.solution_html
    assert '<p>Общий алгоритм:</p><ol>' in plan.solution_html
    assert 'rowspan="3"' not in plan.solution_html
    assert '<td nowrap><span data-inline-latex="k=0"></span></td>' in plan.solution_html
    assert '<td nowrap><span data-inline-latex="x=8+6\\cdot(0)=8"></span></td>' in plan.solution_html
    assert r"x=-4" in plan.solution_html
    assert r"x=8+6\cdot(-2)=-4" in plan.solution_html
    assert "Подставляем" in plan.solution_html
    assert "Выбираем наибольший отрицательный корень" not in plan.solution_html
    assert _ASSETS["cos-half.svg"] in plan.solution_html
    assert not any(item["transformation_target_id"] == "asset:image_1" for item in plan.transformations)


def test_sine_and_tangent_table_values() -> None:
    sin = build_repair_plan(r"\sin\frac{\pi x}{3}=\frac{1}{2}", largest_negative=False)
    tangent = build_repair_plan(r"\tg\frac{\pi(x+2)}{3}=-\sqrt{3}", largest_negative=False)
    assert sin.answer == "0,5"
    assert tangent.answer == "3"
    assert '<p>Общий алгоритм:</p><ol>' in tangent.solution_html
    assert "<th colspan=\"2\" data-align=\"center\" data-cell-tone=\"source-header\" data-valign=\"middle\">Корни</th>" in tangent.solution_html
    assert 'data-inline-latex="x_1"' not in tangent.solution_html
    assert 'data-inline-latex="k=2"' in tangent.solution_html
    assert 'data-inline-latex="x=3"' in tangent.solution_html
    assert r"\frac{\pi x}{3}" in sin.solution_html
    assert r"\pi(x)" not in sin.solution_html
    assert r"\sin \frac{\pi x}{3}=\frac{1}{2}\iff " in sin.solution_html
    assert r"\pi x=\frac{\pi}{2}+6\pi k" in sin.solution_html
    assert sin.solution_html.count(r"x=\frac{1}{2}+6k") == 1
    assert r"x=\frac{1}{2}+6\cdot(-1)=-5{,}5" in sin.solution_html
    assert 'Ближайший к нулю положительный корень: <span data-inline-latex="x=0{,}5"></span>' in sin.solution_html


def test_context_plan_reuses_attached_shared_source_asset() -> None:
    context = _context(r"\tg\frac{\pi x}{4}=-1", "Найдите наибольший отрицательный корень")
    context["normalized_content"]["assets"] = [
        {"asset_key": "shared_a0f23d51d184415f", "asset_id": _ASSETS["tg-minus-one.svg"]}
    ]
    plan = build_context_repair_plan(context)
    assert 'data-asset-key="shared_a0f23d51d184415f"' in plan.solution_html
    assert plan.transformations[0]["value"]["asset_keys"] == ["shared_a0f23d51d184415f"]


def test_asset_selector_chooses_the_exact_library_svg_from_the_condition() -> None:
    context = _context(r"\sin\frac{\pi x}{3}=\frac{1}{2}", "Найдите наименьший положительный корень")
    assert required_assets(context) == ({
        "source_asset_id": _ASSETS["sin-half.svg"],
        "section_id": "solution:1",
        "alt_text": "Табличное значение sin",
    },)


def test_parser_supports_a_positive_integer_coefficient_before_pi() -> None:
    plan = build_repair_plan(
        r"\cos\frac{2\pi x}{6}=\frac{\sqrt{3}}{2}",
        largest_negative=True,
    )
    assert plan.answer == "-0,5"
    assert r"\frac{2\pi x}{6}=\frac{\pi}{6}+2\pi k" in plan.solution_html
    assert r"2\pi x=\pi+12\pi k" in plan.solution_html
    assert r"2x=1+12k" in plan.solution_html
    assert r"x=\frac{1}{2}+6k" in plan.solution_html
