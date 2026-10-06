from solution_runner.pipelines.equations.number_comparison import build_context_repair_plan


def _context(html: str):
    return {"normalized_content": {"format": "teacherhelper-normalized", "schema_version": 3, "sections": [
        {"key": "condition", "html": html, "transformation_target_id": "section:condition:1"},
        {"key": "answer", "html": "<p>?</p>", "transformation_target_id": "section:answer:1"},
    ]}}


def test_selects_the_only_decimal_strictly_between_fraction_bounds():
    plan = build_context_repair_plan(_context(
        '<p>Какое число заключено между <span data-inline-latex="\\frac{5}{9}"></span> и '
        '<span data-inline-latex="\\frac{11}{17}"></span>?</p><ol><li>0,3</li><li>0,4</li><li>0,5</li><li>0,6</li></ol>'
    ))
    assert plan.answer == "4"


def test_selects_the_fraction_at_the_described_number_line_position():
    plan = build_context_repair_plan(_context(
        '<p>Одно из чисел <span data-inline-latex="\\frac{10}{17}"></span>, '
        '<span data-inline-latex="\\frac{11}{17}"></span>, <span data-inline-latex="\\frac{13}{17}"></span> '
        'и <span data-inline-latex="\\frac{14}{17}"></span> отмечено точкой A. '
        'Точка находится в районе 0,76–0,77.</p>'
    ))
    assert plan.answer == "3"


def test_accepts_table_options_and_a_tick_description():
    comparison = build_context_repair_plan(_context(
        '<p>Какое число заключено между <span data-inline-latex="\\frac{13}{15}"></span> и '
        '<span data-inline-latex="\\frac{18}{19}"></span>?</p><table><tr>'
        '<td>1) 0,9</td><td>2) 1</td><td>3) 1,1</td><td>4) 1,2</td></tr></table>'
    ))
    point = build_context_repair_plan(_context(
        '<p>Точкой A отмечено одно из чисел <span data-inline-latex="\\frac{3}{17}"></span>, '
        '<span data-inline-latex="\\frac{4}{17}"></span>, <span data-inline-latex="\\frac{8}{17}"></span> '
        'и <span data-inline-latex="\\frac{14}{17}"></span>. Над делением 0,2 стоит точка.</p>'
    ))
    assert comparison.answer == "1"
    assert point.answer == "1"


def test_accepts_numbered_options_split_by_line_breaks():
    plan = build_context_repair_plan(_context(
        '<p>Какое число заключено между <span data-inline-latex="\\frac{2}{17}"></span> и '
        '<span data-inline-latex="\\frac{4}{19}"></span>? 1) 0<br/>2) 0 ,1<br/>3) 0, 2<br/>4) 0, 3</p>'
    ))
    assert plan.answer == "3"
