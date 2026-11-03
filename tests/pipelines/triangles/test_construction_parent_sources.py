"""Independent Euclidean constructions check every native proof and boundary."""

import gzip
import hashlib
import math
from copy import deepcopy
from fractions import Fraction
from pathlib import Path

import pytest
from bs4 import BeautifulSoup
from construction_source_cases import (
    CASES,
    DATA,
    GROUPS,
    parent_html,
    plan,
    section,
    solution_html,
)

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.equations.trig_parser import TrigonometricParser
from solution_runner.pipelines.triangles.right import construction_parent as runtime

ANGLES = dict(
    zip(
        ("27761", "47259", "47205", "47207", "27765", "47455", "47457", "47459"),
        (58, 67, 4, 39, 32, 56, 20, 30),
    )
)


def vector(a, b):
    return (b[0] - a[0], b[1] - a[1])


def angle(a, o, b):
    u, v = vector(o, a), vector(o, b)
    return math.degrees(
        math.atan2(abs(u[0] * v[1] - u[1] * v[0]), u[0] * v[0] + u[1] * v[1])
    )


def geometry(given, median):
    # Unit hypotenuse; C lies at the origin and its legs lie on the axes.
    alpha = 90 - given if median else given
    a = (math.cos(math.radians(alpha)), 0)
    b = (0, math.sin(math.radians(alpha)))
    c = (0, 0)
    d = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    if median:
        return {
            r"\angle ACD": angle(a, c, d),
            r"\angle A": angle(c, a, b),
            r"\angle B": angle(a, b, c),
            "CD": math.dist(c, d),
            "AD": math.dist(a, d),
            "BD": math.dist(b, d),
        }
    # Intersect angle bisector y=x with the ray from A in the summed unit directions.
    u = vector(a, c)
    v = vector(a, b)
    ulen, vlen = math.hypot(*u), math.hypot(*v)
    direction = (u[0] / ulen + v[0] / vlen, u[1] / ulen + v[1] / vlen)
    t = -a[0] / (direction[0] - direction[1])
    o = (a[0] + t * direction[0], t * direction[1])
    # E is the intersection of y=x with AB.
    e = (a[0] * b[1] / (a[0] + b[1]),) * 2
    return {
        r"\angle CAO": angle(c, a, o),
        r"\angle ACO": angle(a, c, o),
        r"\angle AOE": angle(a, o, e),
        r"\angle C": angle(a, c, b),
        r"\angle A": angle(c, a, b),
    }


def verify(html, values):
    for node in BeautifulSoup(html, "html.parser").select("[data-inline-latex]"):
        statement = node["data-inline-latex"]
        for label, value in sorted(values.items(), key=lambda kv: -len(kv[0])):
            exact = Fraction(value).limit_denominator(100000)
            assert math.isclose(float(exact), value, abs_tol=1e-10)
            statement = statement.replace(
                label, f"({exact.numerator}/{exact.denominator})"
            )
        statement = statement.replace(r"^{\circ}", "")
        numbers = [
            float(TrigonometricParser(p).parse().value) for p in statement.split("=")
        ]
        assert len(numbers) >= 2
        assert all(math.isclose(n, numbers[0], abs_tol=1e-10) for n in numbers), (
            statement
        )


@pytest.mark.parametrize("g", DATA["groups"], ids=lambda g: g["key"])
def test_public_binding_requires_parent_and_rewrites_stale_solution(g):
    profile = get_group_profile(g["key"])
    assert profile.source_group_id == g["group_uuid"] and g["group_size"] >= 3
    assert profile.existing_solution_policy == "rewrite"
    assert ("parent_solution_html", "parent_solution_html") in get_handler(
        g["rule"]
    ).inputs


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_native_answers_and_all_proof_equalities_follow_euclidean_construction(case):
    values = geometry(ANGLES[case["task"]], case["group"] == "27761")
    result = plan(case)
    target = r"\angle ACD" if case["group"] == "27761" else r"\angle AOE"
    assert float(result.answer.replace(",", ".")) == pytest.approx(
        values[target], abs=1e-10
    )
    saved = BeautifulSoup(
        section(case["context"], "answer")["html"], "html.parser"
    ).get_text(strip=True)
    assert float(saved.replace(",", ".")) == pytest.approx(values[target], abs=1e-10)
    verify(solution_html(result), values)
    methods = BeautifulSoup(solution_html(result), "html.parser").select("section")
    assert [m["data-solution-title"] for m in methods] == ["Решение"]
    assert (
        "равнобедренный"
        if case["group"] == "27761"
        else "внешний угол треугольника AOC"
    ) in solution_html(result)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_no_input_mutation_no_old_answer_dependency_no_asset_changes_and_empty_replay(
    case,
):
    ctx = deepcopy(case["context"])
    for key in ("answer", "solution"):
        section(ctx, key)["html"] = "<p>Неверный старый ответ: 999.</p>"
    before = deepcopy(ctx)
    result = plan(case, ctx)
    assert ctx == before and result.answer == plan(case).answer
    for t in result.transformations:
        assert t["transformation_target_id"].startswith(
            ("section:answer", "section:solution")
        )
        next(
            s
            for s in ctx["normalized_content"]["sections"]
            if s["transformation_target_id"] == t["transformation_target_id"]
        ).update(t["value"])
    assert plan(case, ctx).transformations == ()


@pytest.mark.parametrize("group", ["27761", "27765"])
@pytest.mark.parametrize(
    "change", ["instruction", "request", "figure", "nonacute", "markup"]
)
def test_unreviewed_condition_fails_closed(group, change):
    case = next(c for c in CASES if c["group"] == group)
    ctx = deepcopy(case["context"])
    condition = section(ctx, "condition")
    if change == "instruction":
        condition["html"] += "<p>Удвойте ответ.</p>"
    elif change == "request":
        condition["html"] = condition["html"].replace(
            "Най­ди­те", "Вычислите площадь вместо"
        )
    elif change == "figure":
        condition["html"] = condition["html"].replace(
            GROUPS[group]["parent_asset"], "unknown"
        )
    elif change == "nonacute":
        condition["html"] = condition["html"].replace(str(ANGLES[case["task"]]), "90")
    else:
        condition["html"] += "<script>unreviewed</script>"
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize("group", ["27761", "27765"])
@pytest.mark.parametrize("change", ["missing", "method", "formula"])
def test_missing_or_changed_parent_fails_closed(group, change):
    case = next(c for c in CASES if c["group"] == group)
    html = parent_html(group)
    if change == "missing":
        html = ""
    elif change == "method":
        html += "<p>Другой способ решения.</p>"
    else:
        html = html.replace(r"\angle A", r"\angle B")
    with pytest.raises(ContentPlanError):
        plan(case, parent=html)


@pytest.mark.parametrize("group", ["27761", "27765"])
@pytest.mark.parametrize("given", [1, 4, 24, 32, 45, 56, 67, 89, 0.5, 89.5])
def test_both_sides_of_isosceles_and_fractional_angles(group, given):
    case = next(c for c in CASES if c["group"] == group)
    ctx = deepcopy(case["context"])
    section(ctx, "condition")["html"] = section(ctx, "condition")["html"].replace(
        str(ANGLES[case["task"]]), str(given)
    )
    result = plan(case, ctx)
    values = geometry(given, group == "27761")
    verify(solution_html(result), values)
    target = r"\angle ACD" if group == "27761" else r"\angle AOE"
    assert float(result.answer.replace(",", ".")) == pytest.approx(
        values[target], abs=1e-10
    )


def test_original_svg_bytes_are_pinned():
    for source, digest in runtime._SOURCES.items():
        p = Path(runtime.__file__).with_name("assets") / (source + ".svgz")
        assert hashlib.sha256(gzip.decompress(p.read_bytes())).hexdigest() == digest
