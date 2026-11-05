"""Check all figure measurements, volume equalities and rejected incomplete inputs."""

import re
from copy import deepcopy

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from cylinder_cut_source_cases import CASES, plan, read, saved_answer
from midpoint_source_cases import replay, section, solution_html
from sphere_formula_oracle import PiParser

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.solids.cylinder_cut import solve


def verify(result, m):
    a, b, c = m.given
    if m.mode == "sector":
        angle = c if m.kind == "kept" else 360 - c
        quantities = {
            r"V_{\mathrm{цил}}": sp.pi * a * a * b,
            r"\alpha": angle,
            "k": angle / 360,
            "r": a,
            "h": b,
            "V": sp.pi * a * a * b * angle / 360,
        }
    elif m.mode == "stepped":
        quantities = {
            "r": a,
            "H": b,
            "h_1": c,
            "h_2": b - c,
            "V_1": sp.pi * a * a * c,
            "V_2": sp.pi * a * a * (b - c) / 2,
            "V": sp.pi * a * a * c + sp.pi * a * a * (b - c) / 2,
        }
    else:
        quantities = {
            "R": a,
            "r": b,
            "H": c,
            "V_1": sp.pi * a * a * c,
            "V_2": sp.pi * b * b * c,
            "V": sp.pi * (a * a - b * b) * c,
        }
    nodes = BeautifulSoup(solution_html(result), "html.parser").select(
        "[data-inline-latex]"
    )
    assert 5 <= len(nodes) <= 9
    for node in nodes:
        f = (
            node["data-inline-latex"]
            .replace(r"^\circ", "")
            .replace("r^2h", r"r^2\cdot h")
            .replace("R^2H", r"R^2\cdot H")
            .replace("r^2H", r"r^2\cdot H")
            .replace("r^2h_1", r"r^2\cdot h_1")
            .replace("r^2h_2", r"r^2\cdot h_2")
        )
        for name, amount in sorted(quantities.items(), key=lambda p: -len(p[0])):
            f = re.sub(
                r"(?<![A-Za-z_\\])" + re.escape(name) + r"(?![A-Za-z_0-9])",
                lambda _, v=amount: "(" + sp.latex(v) + ")",
                f,
            )
        f = f.replace(r"\pi", r"(\pi)")
        values = [PiParser(v).parse().value for v in f.split("=")]
        assert len(values) > 1 and all(
            sp.simplify(v - values[0]) == 0 for v in values
        ), f
    assert (
        sp.simplify(PiParser(result.answer).parse().value - quantities["V"] / sp.pi)
        == 0
    )


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_all_native_diagrams_compute_without_saved_answers_and_preserve_input(case):
    ctx = deepcopy(case["context"])
    section(ctx, "answer")["html"] = "<p>999</p>"
    before = deepcopy(ctx)
    result = plan(case, ctx)
    assert ctx == before
    assert (
        PiParser(result.answer).parse().value
        == PiParser(saved_answer(case)).parse().value
    )
    verify(result, read(case))
    replay(ctx, result.transformations)
    assert plan(case, ctx).transformations == ()
    assert section(ctx, "condition") == section(before, "condition")
    assert ctx["normalized_content"]["assets"] == before["normalized_content"]["assets"]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize("change", ["missing", "extra", "instruction"])
def test_image_only_dimensions_cannot_be_guessed(case, change):
    ctx = deepcopy(case["context"])
    s = section(ctx, "condition")
    if change == "missing":
        soup = BeautifulSoup(s["html"], "html.parser")
        soup.img.decompose()
        s["html"] = str(soup)
        s["asset_keys"] = []
        ctx["normalized_content"]["assets"] = []
    elif change == "extra":
        s["html"] += "<p>Радиус равен 999.</p>"
    else:
        s["html"] += "<p>Округлите до сотых.</p>"
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize(
    "mode,kind,values,expected",
    [
        ("sector", "kept", ("1.5", 7, 120), sp.Rational(21, 4)),
        ("sector", "removed", (4, 3, 120), 32),
        ("stepped", "", (3, 8, 2), 45),
        ("stepped", "", (3, 2, 2), 18),
        ("annular", "", (5, 3, "1.5"), 24),
    ],
)
def test_general_geometry_not_task_specific(mode, kind, values, expected):
    assert solve(mode, kind, values)[1] == expected


@pytest.mark.parametrize(
    "mode,kind,values",
    [
        ("sector", "kept", (2, 3, 360)),
        ("sector", "unknown", (2, 3, 90)),
        ("stepped", "", (2, 3, 4)),
        ("annular", "", (2, 2, 3)),
        ("annular", "", (2, 3, 4)),
    ],
)
def test_nonphysical_cut_dimensions_are_rejected(mode, kind, values):
    with pytest.raises(ContentPlanError):
        solve(mode, kind, values)


@pytest.mark.parametrize(
    "group", ["27196", "27197", "27198", "27199", "27200", "27201"]
)
@pytest.mark.parametrize("field", ["html", "primary", "assets"])
def test_reviewed_parent_and_source_method_are_required(group, field):
    case = next(c for c in CASES if c["task"] == group)
    from cylinder_cut_source_cases import arguments

    args = arguments(group)
    override = (
        {"parent_solution_html": args["parent_solution_html"] + "<p>Другой метод.</p>"}
        if field == "html"
        else {"parent_asset_id": "foreign"}
        if field == "primary"
        else {"parent_solution_assets": ({"asset_key": "foreign"},)}
    )
    with pytest.raises(ContentPlanError):
        plan(case, **override)
