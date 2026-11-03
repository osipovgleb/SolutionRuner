"""Check native ratios, independent linear equations and frozen local readback."""

import itertools
from copy import deepcopy
from fractions import Fraction

import pytest
from bs4 import BeautifulSoup
from test_general_triangle_ratio_planner import (
    NATIVE,
    PARENT_HTML,
    _materialize,
    _plan,
    _section,
)
from test_two_ray_frozen_lifecycle import OfflineGateway

from solution_runner.pipelines.core.content_runtime import (
    _apply_record,
    _prepared_record,
)
from solution_runner.pipelines.equations.trig_parser import TrigonometricParser
from solution_runner.pipelines.triangles.general.ratio_planner import (
    CONDITION_ASSET_ID,
    RULE,
    build_repair_plan,
)
from solution_runner.pipelines.triangles.right.planner import RightTrianglePlanError

CASES = NATIVE["cases"]
RATIOS = sorted(
    {
        p
        for ratio in [(2, 3, 4), (1, 1, 10), (1, 1, 1), (2, 8, 35), (3, 13, 14)]
        for p in itertools.permutations(ratio)
    }
)


def check_equations(context, ratio):
    unit = Fraction(180, sum(ratio))
    angles = [n * unit for n in ratio]
    assert sum(angles) == 180 and all(0 < a < 180 for a in angles)
    solution = BeautifulSoup(_section(context, "solution")["html"], "html.parser")
    rows = solution.select("center [data-inline-latex]")
    assert len(rows) == (5 if min(ratio) == 1 else 7)
    for row in rows:
        raw = row["data-inline-latex"]
        expression = raw.replace("x", f"({unit})").replace(r"^{\circ}", "")
        sides = [TrigonometricParser(s).parse().value for s in expression.split("=")]
        assert len(sides) == 2 and sides[0] == sides[1], raw


@pytest.mark.parametrize(
    "case,ratio",
    list(zip(CASES, [(2, 3, 4), (1, 1, 10), (2, 8, 35), (1, 1, 1)])),
    ids=[c["task"] for c in CASES],
)
def test_native_answers_preserve_exact_condition_and_empty_repeat(case, ratio):
    ctx = deepcopy(case["context"])
    original = deepcopy(ctx)
    expected = BeautifulSoup(_section(ctx, "answer")["html"], "html.parser").get_text()
    for key in ["solution", "answer"]:
        _section(ctx, key)["html"] = "<p>999</p>"
    before = deepcopy(ctx)
    result = _plan(ctx)
    assert result.answer == expected and ctx == before
    materialized = _materialize(ctx, result)
    assert _section(materialized, "condition") == _section(original, "condition")
    assert (
        materialized["normalized_content"]["assets"]
        == original["normalized_content"]["assets"]
    )
    check_equations(materialized, ratio)
    assert _plan(materialized).transformations == ()


@pytest.mark.parametrize("ratio", RATIOS)
def test_ratio_permutations_use_the_smallest_coefficient(ratio):
    ctx = deepcopy(CASES[0]["context"])
    image = BeautifulSoup(_section(ctx, "condition")["html"], "html.parser").center
    _section(ctx, "condition")["html"] = (
        "<p>Углы треугольника относятся как "
        + " : ".join(map(str, ratio))
        + ". Найдите меньший из них. Ответ дайте в градусах.</p>"
        + str(image)
    )
    result = _plan(ctx)
    assert Fraction(result.answer) == min(ratio) * Fraction(180, sum(ratio))
    check_equations(_materialize(ctx, result), ratio)


@pytest.mark.parametrize(
    "parent,assets",
    [
        ("", ()),
        (PARENT_HTML + "<p>Другой способ</p>", ()),
        (PARENT_HTML, ({"asset_id": "other"},)),
    ],
)
def test_unknown_parent_method_or_images_fail_closed(parent, assets):
    with pytest.raises(RightTrianglePlanError):
        build_repair_plan(
            CASES[0]["context"],
            parent_condition_asset_id=CONDITION_ASSET_ID,
            parent_solution_html=parent,
            parent_solution_assets=assets,
        )


@pytest.mark.parametrize("lost", [False, True])
def test_local_frozen_roundtrip_checks_solution_readback_without_uploads(lost):
    class Gateway(OfflineGateway):
        def apply_problem_transformations(self, identifier, transformations):
            if lost:
                self.writes.append(deepcopy(transformations))
                return {"problem_id": identifier, "applied_count": len(transformations)}
            return super().apply_problem_transformations(identifier, transformations)

    case = CASES[1]
    gateway = Gateway(case)
    kwargs = {"parent_solution_html": PARENT_HTML}
    record = _prepared_record(
        gateway,
        {
            "problem_id": case["context"]["problem_id"],
            "source_problem_id": case["task"],
        },
        CONDITION_ASSET_ID,
        RULE,
        **kwargs,
    )
    assert record["status"] == "prepared" and not gateway.uploads and not gateway.writes
    result = _apply_record(gateway, record, CONDITION_ASSET_ID, RULE, **kwargs)
    assert result["status"] == ("failed" if lost else "applied"), result
    assert not gateway.uploads
    if not lost:
        assert (
            _apply_record(gateway, record, CONDITION_ASSET_ID, RULE, **kwargs)["status"]
            == "already_complete"
        )


@pytest.mark.parametrize("change", ["text", "hidden", "metadata"])
def test_image_wrapper_cannot_hide_extra_facts(change):
    ctx = deepcopy(CASES[0]["context"])
    condition = _section(ctx, "condition")
    if change == "text":
        condition["html"] = condition["html"].replace(
            "<center>", "<center>Удвойте ответ."
        )
    elif change == "hidden":
        condition["html"] = condition["html"].replace(
            "<center>", '<center style="display:none">'
        )
    else:
        ctx["normalized_content"]["assets"].append(None)
    with pytest.raises(RightTrianglePlanError):
        _plan(ctx)
