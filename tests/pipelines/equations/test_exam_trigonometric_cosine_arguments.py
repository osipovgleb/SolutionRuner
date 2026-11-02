"""Original half-angle equations, both cosine branches and audited source circles."""

import gzip
import hashlib
import json
import math
import xml.etree.ElementTree as ET
from copy import deepcopy
from pathlib import Path

import mpmath as mp
import pytest
import sympy as sp
from bs4 import BeautifulSoup

from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.equations.exam_trigonometric import analyze, select
from solution_runner.pipelines.equations.exam_trigonometric_circle import (
    CIRCLES,
    DIRECTORY,
    read,
)
from solution_runner.pipelines.equations.exam_trigonometric_cosine_equality import (
    compile_direct,
    direct_parent,
)
from solution_runner.pipelines.equations.exam_trigonometric_sine_pair import (
    ArgumentPair,
    argument_series,
)
from solution_runner.pipelines.word_problems.common import UnsupportedCondition, section

DATA = json.loads(
    (
        Path(__file__).parent
        / "fixtures/category_14_trigonometric_cosine_arguments.json"
    ).read_text()
)
CASES = DATA["cases"]
R = sp.Rational
X = sp.Symbol("x", real=True)
EXPECTED = {
    "485991": ("0 2/3 4/3", "4/3 2"),
    "510648": ("1/4 5/4", "-7/4 -3/4"),
    "511352": ("5/12 11/12 17/12 23/12", "-19/12 -13/12 -7/12"),
    "501051": ("1/4 5/4", "-7/4 -3/4"),
}


def parent():
    return section(CASES[0]["context"]["normalized_content"], "solution")["html"]


def analysis(c):
    _, f, i, b = read(c["context"])
    return analyze(f, i, b, parent())


def plan(c, context=None):
    return get_handler(get_group_profile(c["group"]).content_rule_key).plan(
        PlanInput(context or c["context"], parent_solution_html=parent())
    )


def original_zero(task, q):
    with mp.workdps(65):
        x = mp.mpf(int(q.p)) / int(q.q) * mp.pi
        if task == "485991":
            value = mp.cos(x / 2) ** 2 - mp.sin(x / 2) ** 2 - mp.sin(mp.pi / 2 - 2 * x)
        elif task == "511352":
            value = mp.sqrt(3) * mp.sin(2 * x) + mp.cos(x) ** 2 - mp.sin(x) ** 2
        else:
            value = mp.sin(x) + mp.sin(x / 2) ** 2 - mp.cos(x / 2) ** 2
        return abs(value) < mp.mpf("1e-48")


def test_full_group_listing_is_eligible_and_reuses_existing_handler():
    tasks = DATA["group_tasks"]
    assert len(tasks) == DATA["group_size"] == 7
    assert len({t["uuid"] for t in tasks}) == 7
    assert {c["context"]["problem_id"] for c in CASES} <= {t["uuid"] for t in tasks}
    p = get_group_profile("485991")
    assert (
        p.source_group_id,
        p.snapshot_theme_id,
        p.theme_order_index,
        p.group_order_index,
    ) == (
        "5c8c36bf-81da-4ce9-8e42-2ccfe348b5fe",
        "81adff3f-4a92-408f-abf4-4881018613e5",
        8,
        3,
    )
    assert p.content_rule_key == "exam-trigonometric-polynomial-circle"


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_full_and_selected_roots_satisfy_original_equations_independently(c):
    a = analysis(c)
    full, selected = (tuple(map(R, text.split())) for text in EXPECTED[c["task"]])
    assert a.argument_pair.cosine
    assert select(a.series, (0, 2, True, False))[0] == full
    assert a.selected == selected
    for q in [*(R(n, 48) for n in range(-216, 217)), *full, *selected]:
        assert original_zero(c["task"], q) == (q % 2 in full)


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_parent_method_replay_and_source_assets_are_preserved(c):
    original = deepcopy(c["context"])
    changed = deepcopy(original)
    for key in ("answer", "solution"):
        section(changed["normalized_content"], key)["html"] = "<p>UNUSED 999</p>"
    p = plan(c, changed)
    assert p == plan(c)
    assert "Косинусы равны" in p.solution_html and r"\tg" not in p.solution_html
    assert p.solution_html.index("<img") < p.solution_html.index("Сведём уравнение")
    for t in p.transformations:
        key = t["transformation_target_id"]
        assert key.startswith(("section:solution", "section:answer"))
        next(
            s
            for s in changed["normalized_content"]["sections"]
            if s["transformation_target_id"] == key
        ).update(t["value"])
    assert plan(c, changed).transformations == ()
    assert c["context"] == original
    assert (
        changed["normalized_content"]["assets"]
        == original["normalized_content"]["assets"]
    )
    assert (
        get_handler(get_group_profile(c["group"]).content_rule_key).diagram_specs(
            original
        )
        == ()
    )
    images = BeautifulSoup(p.solution_html, "html.parser").find_all("img")
    assert [i["src"] for i in images] == [
        a["url"] for a in original["normalized_content"]["assets"]
    ]


def test_contained_series_keeps_zero_instead_of_dividing_by_sine():
    a = analysis(CASES[0])
    assert argument_series(a.argument_pair) == ((0, 2), (0, R(2, 3)))
    assert a.series == ((0, R(2, 3)),)
    assert "Первая серия решений входит во вторую" in plan(CASES[0]).solution_html


def test_false_constant_branch_is_explained_and_true_identity_is_rejected():
    a = analysis(CASES[1])
    assert argument_series(a.argument_pair) == ((R(1, 4), 1),)
    assert "ни при одном целом k" in plan(CASES[1]).solution_html
    with pytest.raises(UnsupportedCondition, match="infinitely many"):
        argument_series(ArgumentPair(X, -X, cosine=True))


def test_amplitude_phase_and_interlaced_series_are_exact():
    a = analysis(CASES[2])
    assert (a.argument_pair.left, a.argument_pair.right, a.argument_pair.weight) == (
        2 * X - sp.pi / 3,
        sp.pi / 2,
        2,
    )
    assert argument_series(a.argument_pair) == ((R(5, 12), 1), (-R(1, 12), 1))
    assert a.series == ((R(5, 12), R(1, 2)),)


@pytest.mark.parametrize(
    "formula",
    [
        r"\cos x=2\cos2x",
        r"\cos x+2\sin x=0",
        r"\cos x=\cos x",
        r"\cos x=\cos(\pi x)",
        r"\cos(x/3)=\cos x",
        r"\cos\alpha=\cos2\alpha",
        r"\frac{\cos x}{\sin x}=\cos2x",
        r"\cos x-\cos2x+1=0",
    ],
)
def test_unsupported_normalizations_fail_closed(formula):
    with pytest.raises(UnsupportedCondition):
        compile_direct(formula)


def test_named_substitution_is_not_silently_dropped_from_parent_method():
    assert direct_parent(parent())
    with pytest.raises(UnsupportedCondition, match="substitution"):
        direct_parent(parent() + '<span data-inline-latex="t=\\cos x"></span>')


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_native_markers_use_original_bytes_and_independent_black_circle(c):
    asset = c["context"]["normalized_content"]["assets"][0]
    entry = CIRCLES[asset["asset_id"]]
    raw = gzip.decompress((DIRECTORY / (asset["asset_id"] + ".svgz")).read_bytes())
    assert hashlib.sha256(raw).hexdigest() == entry["sha256"]
    paths = {n.get("d") for n in ET.fromstring(raw).iter()}
    assert entry["native_circle_path"] in paths and "corrected_file" not in entry
    full = tuple(map(R, EXPECTED[c["task"]][0].split()))
    assert tuple(sorted(R(p["angle"]) for p in entry["green_markers"])) == full
    for p in entry["green_markers"]:
        frame = p["native_frame"]
        assert p["path_d"] in paths and frame["path_d"] == entry["native_circle_path"]
        angle = float(R(p["angle"])) * math.pi
        error = math.hypot(
            p["x"] - frame["cx"] - frame["rx"] * math.cos(angle),
            p["y"] - frame["cy"] + frame["ry"] * math.sin(angle),
        )
        assert error < 5


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_unknown_circle_identity_is_rejected(c):
    changed = deepcopy(c["context"])
    changed["normalized_content"]["assets"][0]["asset_id"] = "unknown"
    with pytest.raises(UnsupportedCondition):
        plan(c, changed)
