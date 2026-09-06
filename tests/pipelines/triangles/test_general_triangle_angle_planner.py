from solution_runner.pipelines.triangles.general.angle_planner import (
    build_repair_plan,
)


def _context(*values: int) -> dict:
    spans = " ".join(
        f'<span data-inline-latex="{value}^{{\\circ}}"></span>' for value in values
    )
    return {
        "normalized_content": {
            "format": "teacherhelper-normalized",
            "schema_version": 3,
            "assets": [],
            "sections": [
                {
                    "key": "condition",
                    "section_id": "condition:1",
                    "html": f"<p>Проверяем углы {spans}</p>",
                },
                {
                    "key": "answer",
                    "section_id": "answer:1",
                    "html": "<p>0</p>",
                },
            ],
        }
    }


def _solution(plan) -> str:
    return next(
        item["value"]["html"]
        for item in plan.transformations
        if "solution" in item["transformation_target_id"]
    )


def test_parent_angle_formulas_are_adapted_to_child_values(monkeypatch) -> None:
    cases = (
        ("general-triangle-27743-exterior-angle", (36, 118), 82, r"118^{\circ}-36^{\circ}=82^{\circ}"),
        ("general-triangle-27757-altitude-angle", (60, 19), 11, r"90^{\circ}-60^{\circ}-19^{\circ}=11^{\circ}"),
        ("general-triangle-27758-bisector-angle", (74, 32), 42, r"2\cdot 32^{\circ}-74^{\circ}=42^{\circ}"),
        ("general-triangle-27759-bisector-exterior-angle", (50, 63), 113, r"\angle CAD=\angle BAD=63^{\circ}"),
        ("general-triangle-27762-orthocenter-angle", (15,), 165, r"90^{\circ}-90^{\circ}-15^{\circ}=165^{\circ}"),
        ("general-triangle-27763-altitudes-angle-sum", (103, 48), 151, r"103^{\circ}+48^{\circ}=151^{\circ}"),
        ("general-triangle-27764-incenter-angle", (110,), 145, r"180^{\circ}-35^{\circ}=145^{\circ}"),
        ("general-triangle-27767-altitude-bisector-intersection", (38,), 128, r"38^{\circ}+90^{\circ}=128^{\circ}"),
    )
    parent_templates = {
        rule: "" for rule, *_ in cases
    }
    parent_templates.update({
        "general-triangle-27743-exterior-angle": '<p><span data-inline-latex="old"></span></p>',
        "general-triangle-27757-altitude-angle": '<p><span data-inline-latex="old"></span></p>',
        "general-triangle-27758-bisector-angle": '<p><span data-inline-latex="old"></span></p>',
        "general-triangle-27759-bisector-exterior-angle": '<p><span data-inline-latex="old"></span><span data-inline-latex="old"></span></p>',
        "general-triangle-27762-orthocenter-angle": '<p><span data-inline-latex="old"></span></p>',
        "general-triangle-27763-altitudes-angle-sum": '<p><span data-inline-latex="old"></span><span data-inline-latex="old"></span></p>',
        "general-triangle-27764-incenter-angle": '<p><span data-inline-latex="old"></span></p>',
        "general-triangle-27767-altitude-bisector-intersection": '<p><span data-inline-latex="old"></span></p>',
    })

    # These tests isolate template adaptation; condition recognition is covered separately.
    from solution_runner.pipelines.triangles.general import angle_planner
    for rule, values, answer, expected in cases:
        monkeypatch.setitem(
            angle_planner.RULES,
            rule,
            (r"Проверяем углы", lambda _match, answer=answer: answer, "unused"),
        )
        plan = build_repair_plan(
            _context(*values),
            rule=rule,
            parent_solution_html=parent_templates[rule],
        )
        assert plan.answer == str(answer)
        assert expected in _solution(plan)


def test_visible_and_inline_values_keep_condition_order(monkeypatch) -> None:
    from solution_runner.pipelines.triangles.general import angle_planner

    rule = "general-triangle-27743-exterior-angle"
    monkeypatch.setitem(
        angle_planner.RULES,
        rule,
        (r"угол A равен\s*(\d+).*B равен\s*(\d+)", lambda match: int(match.group(2)) - int(match.group(1)), "unused"),
    )
    context = _context(129)
    context["normalized_content"]["sections"][0]["html"] = (
        '<p>угол A равен 90°, внешний угол B равен '
        '<span data-inline-latex="129^{\\circ}"></span></p>'
    )
    plan = build_repair_plan(
        context,
        rule=rule,
        parent_solution_html='<p><span data-inline-latex="old"></span></p>',
    )
    assert plan.answer == "39"
    assert r"129^{\circ}-90^{\circ}=39^{\circ}" in _solution(plan)


def test_misplaced_solution_image_is_moved_back_to_condition(monkeypatch) -> None:
    from solution_runner.pipelines.triangles.general import angle_planner

    rule = "general-triangle-27767-altitude-bisector-intersection"
    monkeypatch.setitem(angle_planner.RULES, rule, (r"Проверяем", lambda _match: 128, "unused"))
    context = _context(38)
    context["normalized_content"]["sections"][0]["html"] = (
        '<p>Проверяем <span data-inline-latex="38^{\\circ}"></span></p>'
    )
    context["normalized_content"]["sections"].append(
        {
            "key": "solution",
            "section_id": "solution:1",
            "asset_keys": ["image_1"],
            "html": '<p>old</p><img data-asset-key="image_1"/>',
        }
    )
    plan = build_repair_plan(
        context,
        rule=rule,
        parent_solution_html='<p><span data-inline-latex="old"></span></p>',
        parent_condition_asset_id="parent-asset",
    )
    targets = [item["transformation_target_id"] for item in plan.transformations]
    assert "section:solution:1" in targets
    assert "asset:image_1" in targets
