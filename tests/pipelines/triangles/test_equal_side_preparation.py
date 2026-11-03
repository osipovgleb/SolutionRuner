"""Verify both parent methods against independent equal-side constructions."""

import itertools
import re
from copy import deepcopy

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from equal_side_cases import CASES, GROUPS, PARENTS, parent_html, plan, section
from equal_side_geometry import checked_values
from test_two_ray_frozen_lifecycle import OfflineGateway
from test_two_ray_source_methods import replay

from solution_runner.pipelines.core.content_runtime import (
    _apply_record,
    _prepared_record,
)
from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.equations.trig_parser import TrigonometricParser
from solution_runner.pipelines.triangles.general.equal_side_figures import (
    CONGRUENT,
    EXTENSION,
    SOURCES,
    selection,
    source_bytes,
)

FRAMES = ["".join(p) for p in itertools.permutations("ABC")]
GROUP = {"extension": "27769", "congruent": "27776", "exterior": "27777"}


def synthetic(mode, frame="ABC", values=None):
    case = PARENTS[GROUP[mode]]
    ctx = deepcopy(case["context"])
    image = BeautifulSoup(section(ctx, "condition")["html"], "html.parser").img
    first, second = (
        values
        or {"extension": (44, 62), "congruent": (45, 85), "exterior": (30, 86)}[mode]
    )
    a, b, c = frame
    if mode == "extension":
        text = f"В треугольнике ABC угол {a} равен {first}°, угол {c} равен {second}°. На продолжении стороны {a}{b} за точку {b} отложен отрезок {b}D, равный стороне {b}{c}. Найдите угол D треугольника {b}{c}D. Ответ дайте в градусах."
    elif mode == "congruent":
        text = f"В треугольнике ABC угол {b} равен {first}°, угол {c} равен {second}°. {a}D — биссектриса, E — такая точка на {a}{b}, что {a}E = {a}{c}. Найдите угол {b}DE. Ответ дайте в градусах."
    else:
        text = f"В треугольнике ABC угол {a} равен {first}°, угол {b} равен {second}°. {c}D — биссектриса внешнего угла при вершине {c}, причем точка D лежит на прямой {a}{b}. На продолжении стороны {a}{c} за точку {c} выбрана такая точка E, что {c}E = {c}{b}. Найдите угол {b}DE. Ответ дайте в градусах."
    section(ctx, "condition")["html"] = f"<p>{image}{text}</p>"
    return case, ctx


def check_rows(html, m):
    values, count = checked_values(m)
    reverse = dict(zip(m.frame + "DE", "ABCDE"))
    rows = BeautifulSoup(html, "html.parser").select("center [data-inline-latex]")
    assert len(rows) == count
    for row in rows:
        expression = re.sub(
            r"\\angle\s*([ABCDE]{3}|[ABCDE])",
            lambda match: (
                "(" + sp.latex(values["".join(reverse[n] for n in match[1])]) + ")"
            ),
            row["data-inline-latex"],
        ).replace(r"^{\circ}", "")
        sides = [TrigonometricParser(s).parse().value for s in expression.split("=")]
        assert len(sides) >= 2 and all(sp.simplify(s - sides[0]) == 0 for s in sides), (
            expression
        )


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_native_methods_ignore_stored_results_keep_exact_figures_and_repeat_empty(case):
    ctx = deepcopy(case["context"])
    condition = deepcopy(section(ctx, "condition"))
    expected = BeautifulSoup(section(ctx, "answer")["html"], "html.parser").get_text()
    for key in ["answer", "solution"]:
        section(ctx, key)["html"] = "<p>999</p>"
    before = deepcopy(ctx)
    model = selection(ctx)[0]
    result = plan(case, ctx)
    assert ctx == before and result.answer == expected and not selection(ctx)[-1]
    replay(ctx, result.transformations)
    check_rows(section(ctx, "solution")["html"], model)
    assert (
        section(ctx, "condition") == condition and plan(case, ctx).transformations == ()
    )


@pytest.mark.parametrize("frame", FRAMES)
@pytest.mark.parametrize(
    "mode,values",
    [
        ("extension", (44, 62)),
        ("extension", (100, 13)),
        ("extension", (30, 100)),
        ("congruent", (45, 85)),
        ("congruent", (31, 45)),
        ("congruent", (20, 100)),
    ],
)
def test_both_methods_and_all_vertex_frames_have_valid_geometric_equations(
    mode, values, frame
):
    case, ctx = synthetic(mode, frame, values)
    model = selection(ctx)[0]
    result = plan(case, ctx)
    expected = (180 - sum(values)) / 2 if mode == "extension" else values[1] - values[0]
    assert float(result.answer.replace(",", ".")) == expected
    replay(ctx, result.transformations)
    check_rows(section(ctx, "solution")["html"], model)
    assert plan(case, ctx).transformations == ()


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize("extra", ["Удвойте ответ.", "AB=7.", "Найдите периметр."])
def test_extra_facts_are_never_discarded(case, extra):
    ctx = deepcopy(case["context"])
    section(ctx, "condition")["html"] += f"<p>{extra}</p>"
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize(
    "mode,values",
    [
        ("extension", (0, 62)),
        ("extension", (44, 0)),
        ("extension", (100, 80)),
        ("congruent", (45, 45)),
        ("congruent", (85, 45)),
        ("congruent", (80, 100)),
    ],
)
def test_degenerate_triangles_or_equal_points_outside_the_segment_fail_closed(
    mode, values
):
    case, ctx = synthetic(mode, values=values)
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize(
    "mode,old,new",
    [
        ("extension", "за точку B", "за точку A"),
        ("extension", "отрезок BD", "отрезок AD"),
        ("extension", "стороне BC", "стороне AC"),
        ("extension", "треугольника BCD", "треугольника ABD"),
        ("congruent", "AD — биссектриса", "AD — внешняя биссектриса"),
        ("congruent", "точка на AB", "точка на AC"),
        ("congruent", "AE = AC", "AE = AD"),
        ("congruent", "угол BDE", "угол CDE"),
    ],
)
def test_changed_side_roles_or_target_angle_are_rejected(mode, old, new):
    case, ctx = synthetic(mode)
    section(ctx, "condition")["html"] = section(ctx, "condition")["html"].replace(
        old, new
    )
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize("mode", ["extension", "congruent"])
@pytest.mark.parametrize("frame,lost", [("ABC", False), ("CAB", False), ("CAB", True)])
def test_local_frozen_roundtrip_preserves_source_style_and_authoritative_readback(
    mode, frame, lost
):
    case, ctx = synthetic(mode, frame)
    gateway = OfflineGateway({**case, "context": ctx}, omit_condition_write=lost)
    rule = GROUPS[case["group"]]["rule"]
    source = SOURCES[mode]
    kwargs = {"parent_solution_html": parent_html(case["group"])}
    record = _prepared_record(
        gateway,
        {"problem_id": ctx["problem_id"], "source_problem_id": case["task"]},
        source,
        rule,
        **kwargs,
    )
    assert record["status"] == "prepared" and not gateway.uploads and not gateway.writes
    result = _apply_record(gateway, record, source, rule, **kwargs)
    assert result["status"] == ("failed" if lost else "applied"), result
    assert len(gateway.uploads) == int(frame != "ABC")
    if not lost:
        assert (
            _apply_record(gateway, record, source, rule, **kwargs)["status"]
            == "already_complete"
        )


@pytest.mark.parametrize("group", list(GROUPS))
def test_changed_parent_method_is_rejected(group):
    with pytest.raises(ContentPlanError):
        plan(PARENTS[group], parent=parent_html(group) + "<p>Другой способ</p>")


@pytest.mark.parametrize("mode", ["extension", "congruent"])
def test_a_different_reviewed_source_cannot_substitute_for_the_required_construction(
    mode,
):
    case, ctx = synthetic(mode)
    old = SOURCES[mode]
    other = CONGRUENT if mode == "extension" else EXTENSION
    ctx["normalized_content"]["assets"][0]["asset_id"] = other
    ctx["normalized_content"]["assets"][0]["url"] = "/assets/" + other
    section(ctx, "condition")["html"] = section(ctx, "condition")["html"].replace(
        old, other
    )
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize("mode", ["extension", "congruent"])
def test_another_complete_construction_cannot_use_the_current_registered_method(mode):
    case, _ = synthetic(mode)
    _, other = synthetic("congruent" if mode == "extension" else "extension")
    with pytest.raises(ContentPlanError):
        plan(case, other)


@pytest.mark.parametrize("change", ["extra", "unknown", "reference", "url"])
def test_unreviewed_asset_metadata_and_references_fail_closed(change):
    case, ctx = synthetic("congruent")
    asset = ctx["normalized_content"]["assets"][0]
    if change == "extra":
        ctx["normalized_content"]["assets"].append({"asset_key": "image_2"})
    elif change == "unknown":
        asset["asset_id"] = "unknown"
        asset["url"] = "/assets/unknown"
    elif change == "reference":
        section(ctx, "condition")["html"] = section(ctx, "condition")["html"].replace(
            CONGRUENT, "unknown"
        )
    else:
        asset["url"] = "/assets/unknown"
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize("source", [EXTENSION, CONGRUENT])
def test_both_reviewed_sources_are_packaged_and_hash_pinned(source):
    assert source_bytes(source).lstrip().startswith((b"<?xml", b"<svg"))


@pytest.mark.parametrize(
    "mode,old,new",
    [
        ("extension", "стороне BC", "стороне CB"),
        ("extension", "треугольника BCD", "треугольника DCB"),
        ("congruent", "AE = AC", "CA = EA"),
        ("congruent", "угол BDE", "угол EDB"),
    ],
)
def test_equivalent_segment_and_triangle_orders_keep_the_answer(mode, old, new):
    case, ctx = synthetic(mode)
    section(ctx, "condition")["html"] = section(ctx, "condition")["html"].replace(
        old, new
    )
    assert plan(case, ctx).answer == ("37" if mode == "extension" else "40")


@pytest.mark.parametrize(
    "mode,values,expected",
    [("extension", ("44{,}5", 62), "36,75"), ("congruent", ("45{,}5", 85), "39,5")],
)
def test_exact_fractional_degree_results(mode, values, expected):
    case, ctx = synthetic(mode, values=values)
    model = selection(ctx)[0]
    result = plan(case, ctx)
    assert result.answer == expected
    replay(ctx, result.transformations)
    check_rows(section(ctx, "solution")["html"], model)
