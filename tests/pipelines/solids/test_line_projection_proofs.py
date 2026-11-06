"""All native projection proof steps and the existing child method order."""

from dataclasses import replace

import pytest
from line_projection_equation_oracle import verify
from midpoint_source_cases import section
from test_line_projection_models import CASES

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.solids.spatial_distance_model import read_question
from solution_runner.pipelines.solids.spatial_distance_proofs import render


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_runtime_reader_and_every_native_projection_equation(case):
    m = read_question(section(case["context"], "condition")["html"])
    pics = {}
    if len(case["context"]["normalized_content"]["assets"]) == 2:
        m = replace(m, symbols={"method": "median"})
        pics = {"image_2": '<img data-asset-key="image_2"/>'}
    html = render(m, pics)
    verify(html, m)
    assert html.count("SA ⟂ AB") == (1 if case["group"] == "513098" else 0)
    if pics:
        assert html.index("Пусть O") < html.index("Метод координат")
        assert "Продолжении AB" not in html


@pytest.mark.parametrize("term", ("равногранным", "рав\xadно\xadгран\xadным"))
def test_reviewed_italic_glossary_normalization_preserves_condition_meaning(term):
    case = next(c for c in CASES if c["group"] == "507576")
    html = section(case["context"], "condition")["html"]
    old = "<i>рав\xadно\xadгран\xadным</i>"
    assert old in html
    assert (
        read_question(html.replace(old, "<i>" + term + "</i>")).mode
        == "box_tetrahedron_line_projection_angle"
    )
    for replacement in (
        "<i>unknown</i>",
        '<i class="changed">равногранным</i>',
        "<i><b>равногранным</b></i>",
    ):
        with pytest.raises(ContentPlanError):
            read_question(html.replace(old, replacement))
