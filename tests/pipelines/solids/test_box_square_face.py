"""Check independent trigonometric volumes, exact figure reuse and local lifecycle."""

import re
from copy import deepcopy

import pytest
import sympy as sp
from box_square_face_source_cases import CASES, arguments, plan, read, saved_answer
from bs4 import BeautifulSoup
from midpoint_source_cases import replay, section, solution_html
from test_midpoint_area_lifecycle import OfflineGateway

from solution_runner.pipelines.core.content_runtime import (
    _apply_record,
    _prepared_record,
)
from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.equations.logarithm_parser import LogarithmParser
from solution_runner.pipelines.equations.power_arithmetic import ScalarParser
from solution_runner.pipelines.quadrilaterals.parallelogram.rectangle_proofs import (
    value,
)
from solution_runner.pipelines.solids.box_sources import SOURCES, source_bytes
from solution_runner.pipelines.solids.box_square_face_figures import (
    CONDITION,
    SOLUTION,
    SYMBOLIC,
)

RULE = "solid-box-square-face-volume"
SINES = {
    sp.Integer(15): (sp.sqrt(6) - sp.sqrt(2)) / 4,
    sp.Rational(45, 2): sp.sqrt(2 - sp.sqrt(2)) / 2,
    sp.Integer(30): sp.Rational(1, 2),
    sp.Integer(45): sp.sqrt(2) / 2,
    sp.Integer(60): sp.sqrt(3) / 2,
    sp.Integer(75): (sp.sqrt(6) + sp.sqrt(2)) / 4,
}


def condition(d, angle):
    return (
        "<p>Одна из граней прямоугольного параллелепипеда — квадрат. Диагональ параллелепипеда равна "
        + str(d)
        + " и образует с плоскостью этой грани угол "
        + str(angle)
        + "°. Найдите объем параллелепипеда.</p>"
    )


def verify_proof(result, diagonal, angle):
    sine = SINES[angle]
    cosine = sp.sqrt(sp.simplify(1 - sine**2))
    h = sp.simplify(diagonal * sine)
    q = sp.simplify(diagonal * cosine)
    area = sp.simplify(q**2 / 2)
    volume = sp.simplify(area * h)
    variables = {"d": diagonal, "h": h, "q": q, "S": area, "V": volume}
    for node in BeautifulSoup(solution_html(result), "html.parser").select(
        "[data-inline-latex]"
    ):
        f = (
            node["data-inline-latex"]
            .replace(r"\sin " + value(angle) + r"^{\circ}", "(" + sp.latex(sine) + ")")
            .replace(
                r"\cos " + value(angle) + r"^{\circ}", "(" + sp.latex(cosine) + ")"
            )
            .replace("Sh", "S*h")
        )
        f = re.sub(
            r"(?<![A-Za-z\\])([dhqSV])(?![A-Za-z])",
            lambda m: "(" + sp.latex(variables[m[1]]) + ")",
            f,
        )
        parts = [LogarithmParser(t).parse().value for t in f.split("=")]
        assert len(parts) > 1 and all(sp.simplify(t - parts[0]) == 0 for t in parts), f
    assert sp.simplify(LogarithmParser(result.answer).parse().value - volume) == 0


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_native_exact_volume_proofs_immutable_inputs_and_existing_sources(case):
    ctx = deepcopy(case["context"])
    section(ctx, "answer")["html"] = "<p>999</p>"
    before = deepcopy(ctx)
    m = read(case)
    result = plan(case, ctx)
    assert (
        ctx == before
        and sp.simplify(
            ScalarParser(result.answer).parse()
            - ScalarParser(saved_answer(case)).parse()
        )
        == 0
    )
    verify_proof(result, *m.given)
    assert ("равнобедренный" in solution_html(result)) == (m.given[1] == 45)
    assert get_handler(RULE).diagram_specs(ctx) == ()
    replay(ctx, result.transformations)
    assert plan(case, ctx).transformations == () and section(ctx, "source") == section(
        before, "source"
    )
    assets = {
        a["asset_key"]: a["asset_id"] for a in ctx["normalized_content"]["assets"]
    }
    assert assets == {
        "image_1": CONDITION,
        "image_2": SYMBOLIC if case["task"] == "324301" else SOLUTION,
    }
    assert {a["asset_id"] for a in before["normalized_content"]["assets"]} <= set(
        assets.values()
    )
    assert section(ctx, "condition")["asset_keys"] == ["image_1"] and section(
        ctx, "solution"
    )["asset_keys"] == ["image_2"]


@pytest.mark.parametrize("angle", SINES)
@pytest.mark.parametrize("d", [sp.Rational(3, 2), sp.sqrt(7), sp.Integer(10)])
def test_exact_angle_family_has_positive_real_edges_correct_volume_and_no_new_svgs(
    angle, d
):
    case = CASES[-1]
    ctx = deepcopy(case["context"])
    section(ctx, "condition")["html"] = condition(
        sp.latex(d), value(angle).replace("{,}", ",")
    )
    result = plan(case, ctx)
    m = read({**case, "context": ctx})
    verify_proof(result, d, angle)
    a, b, h = m.edges
    assert a == b and all(v.is_positive is True for v in (a, b, h))
    assert sp.simplify(a * a + b * b + h * h - d * d) == 0
    replay(ctx, result.transformations)
    assert plan(case, ctx).transformations == ()


@pytest.mark.parametrize(
    "d,angle",
    [
        ("0", "45"),
        ("-2", "45"),
        ("2", "0"),
        ("2", "90"),
        ("2", "120"),
        ("2", "-30"),
        ("2", "17"),
        ("2", r"\sqrt{2}"),
    ],
)
def test_nonphysical_or_non_elementary_measurements_fail_closed(d, angle):
    ctx = deepcopy(CASES[-1]["context"])
    section(ctx, "condition")["html"] = condition(d, angle)
    with pytest.raises(ContentPlanError):
        plan(CASES[-1], ctx)


@pytest.mark.parametrize("field", ["html", "primary", "assets"])
def test_parent_pins_and_strict_profile(field):
    args = arguments("27103")
    override = (
        {"parent_solution_html": args["parent_solution_html"] + "<p>Другой метод.</p>"}
        if field == "html"
        else {"parent_asset_id": "foreign"}
        if field == "primary"
        else {"parent_solution_assets": ()}
    )
    with pytest.raises(ContentPlanError):
        plan(CASES[0], **override)
    profile = get_group_profile("27103")
    handler = get_handler(RULE)
    handler.validate()
    assert (
        profile.source_group_id == "8f5f72ae-5105-476a-ac5b-a3f523c36fdd"
        and profile.group_order_index == 9
    )
    assert (
        handler.requires_frozen_manifest
        and handler.strict_frozen_input
        and handler.verify_content_readback
    )


@pytest.mark.parametrize("case", CASES[:3], ids=lambda c: c["task"])
@pytest.mark.parametrize(
    "field", ["foreign", "url", "duplicate", "unreferenced", "instruction", "role"]
)
def test_unreviewed_asset_metadata_instructions_and_roles_fail_closed(case, field):
    ctx = deepcopy(case["context"])
    assets = ctx["normalized_content"]["assets"]
    a = assets[0]
    if field == "foreign":
        a["asset_id"] = "foreign"
    elif field == "url":
        a["url"] = "https://example.com/foreign.svg"
    elif field == "duplicate":
        assets.append(deepcopy(a))
    elif field == "unreferenced":
        for s in ctx["normalized_content"]["sections"]:
            soup = BeautifulSoup(s["html"], "html.parser")
            for img in soup.find_all("img"):
                if img.get("data-asset-key") == a["asset_key"]:
                    img.decompose()
            s["html"] = str(soup)
            s["asset_keys"] = [
                k for k in s.get("asset_keys", []) if k != a["asset_key"]
            ]
    elif field == "role":
        # A projection-only solution source cannot replace the condition source.
        a["asset_id"] = SYMBOLIC if a["asset_id"] == CONDITION else CONDITION
    else:
        section(ctx, "condition")["html"] += "<p>Округлите до сотых.</p>"
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize("source", [CONDITION, SOLUTION, SYMBOLIC])
def test_reviewed_bytes_remain_exact(source):
    import hashlib

    assert hashlib.sha256(source_bytes(source)).hexdigest() == SOURCES[source][1]


def prepared(case, gateway):
    return _prepared_record(
        gateway,
        {
            "problem_id": case["context"]["problem_id"],
            "source_problem_id": case["task"],
        },
        content_rule_key=RULE,
        **arguments("27103"),
    )


def apply_offline(case, gateway, record):
    return _apply_record(gateway, record, content_rule_key=RULE, **arguments("27103"))


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_native_prepare_no_side_effect_then_local_roundtrip_and_resume(case):
    gateway = OfflineGateway(case)
    record = prepared(case, gateway)
    assert (
        record["status"] == "prepared"
        and not record["generated_diagrams"]
        and not gateway.uploads
        and not gateway.writes
    )
    assert apply_offline(case, gateway, record)["status"] == "applied"
    assert len(gateway.writes) == 1 and not gateway.uploads
    assert apply_offline(case, gateway, record)["status"] == "already_complete"
    assert len(gateway.writes) == 1


@pytest.mark.parametrize("task", ["324301", "324303"])
@pytest.mark.parametrize(
    "target",
    ["asset:image_1", "asset:image_2", "section:condition:1", "section:solution:1"],
)
def test_restored_or_legacy_key_roles_require_full_readback(task, target):
    case = next(c for c in CASES if c["task"] == task)
    gateway = OfflineGateway(case)
    record = prepared(case, gateway)
    if task == "324303" and target == "section:solution:1":
        target = "section:solution"
    assert target in {t["transformation_target_id"] for t in record["transformations"]}
    gateway.omit = target
    assert apply_offline(case, gateway, record)["status"] == "failed"


@pytest.mark.parametrize("drift", ["condition", "answer"])
def test_frozen_drift_blocks_before_any_local_write(drift):
    case = CASES[-1]
    gateway = OfflineGateway(case)
    record = prepared(case, gateway)
    section(gateway.context, drift)["html"] += "<p>Изменено.</p>"
    assert apply_offline(case, gateway, record)["status"] in {"failed", "blocked"}
    assert not gateway.writes and not gateway.uploads
