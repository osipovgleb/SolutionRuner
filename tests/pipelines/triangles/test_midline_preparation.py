"""Check all midline parent cases against independent polygon areas and frozen replay."""

import re
from copy import deepcopy

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from midline_cases import CASES, GROUPS, PARENTS, parent_html, plan, section
from test_two_ray_frozen_lifecycle import OfflineGateway
from test_two_ray_source_methods import replay

from solution_runner.pipelines.core.content_runtime import (
    _apply_record,
    _prepared_record,
    _solution_assets,
)
from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.equations.trig_parser import TrigonometricParser
from solution_runner.pipelines.triangles.general.midline_figures import (
    SECOND,
    SOURCES,
    selection,
    source_bytes,
)


def points(model, second=False):
    a, b, c = map(sp.Matrix, [(0, 0), (10, 0), (7, 8)])
    canonical = dict(
        zip("ABCDE", [a, b, c, (a + c) / 2, (a + b) / 2 if second else (b + c) / 2])
    )
    return {model.mapping[name]: value for name, value in canonical.items()}


def area(coords, name):
    vertices = [coords[c] for c in name]
    return (
        abs(
            sum(
                sp.det(sp.Matrix.hstack(a, b))
                for a, b in zip(vertices, vertices[1:] + vertices[:1])
            )
        )
        / 2
    )


def check_rows(html, model):
    rows = BeautifulSoup(html, "html.parser").select("[data-inline-latex]")
    for index, row in enumerate(rows):
        coords = points(model, model.mode == "total" and index >= 3)
        unit_given = area(coords, model.name("CDE") if model.mode == "total" else "ABC")
        scale = model.given / unit_given
        raw = row["data-inline-latex"]
        text = re.sub(
            r"S_\{([ABCDE]{3,4})\}",
            lambda m, coords=coords, scale=scale: (
                "(" + sp.latex(area(coords, m[1]) * scale) + ")"
            ),
            raw,
        )
        text = text.replace("k", "(2)" if model.mode == "total" else r"(\frac{1}{2})")
        terms = [TrigonometricParser(term).parse().value for term in text.split("=")]
        assert len(terms) > 1 and all(sp.simplify(t - terms[0]) == 0 for t in terms), (
            raw
        )


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_native_answers_all_parent_cases_and_empty_repeat(case):
    ctx = deepcopy(case["context"])
    expected = BeautifulSoup(section(ctx, "answer")["html"], "html.parser").get_text()
    condition = section(ctx, "condition")["html"]
    for key in ("answer", "solution"):
        section(ctx, key)["html"] = "<p>Не использовать: 999.</p>"
    original = deepcopy(ctx)
    result = plan(case, ctx)
    assert ctx == original and result.answer == expected
    model = selection(ctx)[0]
    replay(ctx, result.transformations)
    html = section(ctx, "solution")["html"]
    check_rows(html, model)
    assert plan(case, ctx).transformations == ()
    if model.mode == "total":
        assert "1. Средняя линия" in html and "2. Средняя линия" in html
        assert "исключена" not in html and "-------" not in html
        image = BeautifulSoup(html, "html.parser").img
        assert image and html.index("2. Средняя линия") < html.index(str(image))
    else:
        assert not BeautifulSoup(html, "html.parser").find("img")
    before, after = (
        BeautifulSoup(t, "html.parser")
        for t in [condition, section(ctx, "condition")["html"]]
    )
    before.img.decompose()
    after.img.decompose()
    assert str(before) == str(after)
    if model.vertex == "C":
        assert condition == section(ctx, "condition")["html"]


def synthetic(mode, vertex, value="17{,}5"):
    group = {"small": "27592", "total": "317337", "trapezoid": "319058"}[mode]
    case = PARENTS[group]
    ctx = deepcopy(case["context"])
    image = BeautifulSoup(section(ctx, "condition")["html"], "html.parser").img
    base = "".join(sorted(set("ABC") - {vertex}))
    if mode == "total":
        text = f"В треугольнике ABC DE — средняя линия. Площадь треугольника {vertex}DE равна {value}. Найдите площадь треугольника ABC."
    else:
        target = f"треугольника {vertex}DE" if mode == "small" else f"трапеции {base}ED"
        text = f"Площадь треугольника ABC равна {value}, DE — средняя линия, параллельная стороне {base}. Найдите площадь {target}."
    section(ctx, "condition")["html"] = f"<p>{image}{text}</p>"
    return case, ctx


@pytest.mark.parametrize("mode", ["small", "total", "trapezoid"])
@pytest.mark.parametrize("vertex", list("ABC"))
@pytest.mark.parametrize("value", ["12", "17{,}5", r"\frac{7}{2}"])
def test_direct_inverse_and_trapezoid_share_exact_geometry(mode, vertex, value):
    case, ctx = synthetic(mode, vertex, value)
    result = plan(case, ctx)
    model = selection(ctx)[0]
    original = TrigonometricParser(value).parse().value
    expected = (
        original
        * {"small": sp.Rational(1, 4), "total": 4, "trapezoid": sp.Rational(3, 4)}[mode]
    )
    assert sp.Rational(result.answer.replace(",", ".")) == expected
    replay(ctx, result.transformations)
    check_rows(section(ctx, "solution")["html"], model)
    assert plan(case, ctx).transformations == ()


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize("extra", ["Удвойте ответ.", "AB=7.", "Найдите периметр."])
def test_additional_facts_are_not_discarded(case, extra):
    ctx = deepcopy(case["context"])
    section(ctx, "condition")["html"] += f"<p>{extra}</p>"
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize(
    "mode,vertex,lost",
    [
        ("small", "C", False),
        ("total", "C", False),
        ("total", "B", False),
        ("total", "B", True),
        ("trapezoid", "A", False),
    ],
)
def test_local_frozen_figures_uuid_and_authoritative_readback(mode, vertex, lost):
    case, ctx = synthetic(mode, vertex)
    gateway = OfflineGateway({**case, "context": ctx}, omit_condition_write=lost)
    source = SOURCES[mode]
    rule = GROUPS[case["group"]]["rule"]
    kwargs = {
        "parent_solution_html": parent_html(case["group"]),
        "parent_solution_assets": _solution_assets(PARENTS[case["group"]]["context"]),
    }
    record = _prepared_record(
        gateway,
        {"problem_id": ctx["problem_id"], "source_problem_id": case["task"]},
        source,
        rule,
        **kwargs,
    )
    assert record["status"] == "prepared", record
    assert not gateway.uploads and not gateway.writes
    result = _apply_record(gateway, record, source, rule, **kwargs)
    assert result["status"] == ("failed" if lost else "applied"), result
    assert len(gateway.uploads) == (0 if vertex == "C" else 2 if mode == "total" else 1)
    if not lost:
        assert (
            _apply_record(gateway, record, source, rule, **kwargs)["status"]
            == "already_complete"
        )


@pytest.mark.parametrize("group", list(GROUPS))
def test_parent_methods_are_pinned_and_bindings_rewrite(group):
    with pytest.raises(ContentPlanError):
        plan(PARENTS[group], parent=parent_html(group) + "<p>Другой способ.</p>")
    profile = get_group_profile(group)
    handler = get_handler(profile.content_rule_key)
    assert profile.existing_solution_policy == "rewrite"
    assert handler.target.endswith("midline_parent:prepare")
    assert handler.requires_frozen_manifest and handler.verify_content_readback


@pytest.mark.parametrize("kind", ["duplicate", "extra", "unknown", "url", "reference"])
def test_unreviewed_or_inconsistent_assets_are_rejected(kind):
    case, ctx = synthetic("total", "C")
    asset = ctx["normalized_content"]["assets"][0]
    if kind == "duplicate":
        ctx["normalized_content"]["assets"].append(deepcopy(asset))
    elif kind == "extra":
        ctx["normalized_content"]["assets"].append({"asset_key": "image_3"})
    elif kind == "unknown":
        asset["asset_id"] = "other"
        asset["url"] = "/assets/other"
    elif kind == "url":
        asset["url"] = "/assets/other"
    else:
        section(ctx, "condition")["html"] = section(ctx, "condition")["html"].replace(
            asset["asset_id"], "other"
        )
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize(
    "old,new",
    [
        ("DE — средняя линия", "DE — медиана"),
        ("AB.", "AC."),
        ("CDE.", "ABC."),
        ("17{,}5", "0"),
        ("17{,}5", "-2"),
        ("DE — средняя линия", "DE — средняя линия, DE — средняя линия"),
    ],
)
def test_missing_or_contradictory_midline_facts_fail_closed(old, new):
    case, ctx = synthetic("small", "C")
    section(ctx, "condition")["html"] = section(ctx, "condition")["html"].replace(
        old, new
    )
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize("source", [*SOURCES.values(), SECOND])
def test_reviewed_midline_sources_are_packaged_and_hash_pinned(source):
    assert source_bytes(source).lstrip().startswith((b"<?xml", b"<svg"))
