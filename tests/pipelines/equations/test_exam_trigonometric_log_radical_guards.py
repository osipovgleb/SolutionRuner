"""Unreviewed radical-log products cannot cancel original domains or source methods."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.equations.exam_trigonometric_log_radical import (
    compile_product,
)
from solution_runner.pipelines.word_problems.common import UnsupportedCondition, section

DATA = json.loads(
    (
        Path(__file__).parent / "fixtures/category_14_trigonometric_log_radicals.json"
    ).read_text()
)


def case(key):
    return next(c for c in DATA["cases"] if c["task"] == key)


def prototype(key):
    return section(case(key)["context"]["normalized_content"], "solution")["html"]


@pytest.mark.parametrize(
    "formula",
    [
        r"\sqrt{2\sin x+\sqrt{2}}+\log_4(2\cos x)=0",
        r"\sqrt{2\sin x+\sqrt{2}}\log_4^2(2\cos x)=0",
        r"\sqrt{2\sin x+\sqrt{2}}\log_{\cos x}(2\cos x)=0",
        r"\sqrt{2\sin x+\sqrt{2}}\log_1(2\cos x)=0",
        r"\sqrt{2\sin x+\sqrt{2}}\log_4(2\sin x)=0",
        r"\sqrt{2\sin x+\sqrt{2}}\log_4(2\cos x+1)=0",
        r"\sqrt{2\sin^2x+\sqrt{2}}\log_4(2\cos x)=0",
        r"\sqrt{2\sin x-\sqrt{2}}\log_4(2\cos x)=0",
        r"\sqrt{2\sin x+3}\log_4(2\cos x)=0",
        r"\sqrt{2\sin x+\sqrt{2}}\log_4(2\cos x)\log_4(2\cos x)=0",
        r"\frac{\sqrt{2\sin x+\sqrt{2}}}{\log_4(2\cos x)}=0",
        r"\sqrt{2\sin x+\sqrt{2}}\sqrt{\cos x}\log_4(2\cos x)=0",
        r"\sqrt{2\sin x+\sqrt{2}}\log_4(\sqrt{2\cos x})=0",
        r"\sqrt{\sqrt{2\sin x+\sqrt{2}}}\log_4(2\cos x)=0",
        r"\sqrt{2\sin x+\sqrt{2}}^2\log_4(2\cos x)=0",
        r"(\sin x)\sqrt{2\sin x+\sqrt{2}}\log_4(2\cos x)=0",
        r"\frac{\sqrt{2\sin x+\sqrt{2}}}{\sqrt{2\sin x+\sqrt{2}}}\log_4(2\cos x)=0",
    ],
)
def test_extra_log_powers_unreviewed_root_domains_and_cancellation_fail_closed(formula):
    with pytest.raises(UnsupportedCondition):
        compile_product(formula, prototype("632828"))


@pytest.mark.parametrize(
    "formula",
    [
        r"\frac{\sqrt{2\sin x+\sqrt{2}}\log_3(-2\cos x)}{\sqrt{\tg x}}=0",
        r"\frac{\sqrt{2\sin x+\sqrt{2}}\log_3(2\cos x)}{\sqrt{-\tg x}}=0",
        r"\frac{\sqrt{2\sin x-\sqrt{2}}\log_3(-2\cos x)}{\sqrt{-\tg x}}=0",
        r"\frac{\sqrt{2\sin x+\sqrt{2}}\log_3(-2\cos x)}{\sqrt{1-\tg x}}=0",
        r"\frac{\sqrt{2\sin x+\sqrt{2}}\log_3(-2\cos x)}{\sqrt{-\ctg x}}=0",
    ],
)
def test_parent_cancellation_requires_a_proof_for_the_actual_child_domain(formula):
    with pytest.raises(UnsupportedCondition):
        compile_product(formula, prototype("700451"))


def test_deleted_alternative_heading_or_missing_companion_cannot_drop_a_parent_method():
    c = case("632828")
    h = get_handler(get_group_profile(c["group"]).content_rule_key)
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(prototype("632828"), "html.parser")
    for node in soup.find_all(string=True):
        if "изложим решение пункта а) иначе" in str(node).replace("\xad", "").lower():
            node.replace_with("Способ удалён.")
    with pytest.raises(UnsupportedCondition):
        h.plan(PlanInput(c["context"], parent_solution_html=str(soup)))
    for index in (0, 1):
        ctx = deepcopy(c["context"])
        ctx["normalized_content"]["assets"].pop(index)
        with pytest.raises(UnsupportedCondition):
            h.plan(PlanInput(ctx, parent_solution_html=prototype("632828")))


def test_the_two_source_circles_cannot_swap_roles_or_receive_an_unneeded_duplicate():
    c = case("632828")
    h = get_handler(get_group_profile(c["group"]).content_rule_key)
    ctx = deepcopy(c["context"])
    ctx["normalized_content"]["assets"].reverse()
    with pytest.raises(UnsupportedCondition):
        h.plan(PlanInput(ctx, parent_solution_html=prototype("632828")))
    with pytest.raises(UnsupportedCondition):
        h.plan(
            PlanInput(
                c["context"],
                parent_solution_html=prototype("632828"),
                generated_solution_assets=(
                    {
                        "asset_key": "exam_trig_circle",
                        "sha256": "0" * 64,
                        "source_asset_id": "duplicate",
                        "url": "/assets/duplicate",
                    },
                ),
            )
        )


def test_unknown_parent_cannot_invent_a_cancellation_or_an_extra_method():
    for text in (
        "<p>Сократите корни и решите численно.</p>",
        prototype("700451").replace("со\u00adкра\u00adтить", "заменить"),
    ):
        with pytest.raises(UnsupportedCondition):
            compile_product(
                r"\frac{\sqrt{2\sin x+\sqrt{2}}\log_3(-2\cos x)}{\sqrt{-\tg x}}=0", text
            )
