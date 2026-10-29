from copy import deepcopy

import pytest

from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.informatics.password_extra_bytes import build_context_repair_plan
from solution_runner.pipelines.word_problems.common import UnsupportedCondition


def context(size=12, length=15, users=20, total=400, *, solution=False):
    symbols = ", ".join("АВCDЕFGHKLMN"[:size])
    text = (
        f"При регистрации в компьютерной системе каждому пользователю выдаётся пароль, состоящий из <nobr>{length} символов</nobr> "
        f"и содержащий только символы из {size}-\u2060символьного набора: {symbols}. "
        "В базе данных для хранения сведений о каждом пользователе отведено одинаковое и минимально возможное целое число байт. "
        "При этом используют посимвольное кодирование паролей, все символы кодируют одинаковым и минимально возможным количеством бит. "
        "Кроме собственно пароля, для каждого пользователя в системе хранятся дополнительные сведения, для чего выделено целое число байт; "
        "это число одно и то же для всех пользователей. "
        f"Для хранения сведений о {users} пользователях потребовалось {total} байт. "
        "Сколько байт выделено для хранения дополнительных сведений об одном пользователе? "
        "В ответе запишите только целое число — количество байт."
    )
    sections = [{"key": "condition", "html": f"<p>{text}</p>", "asset_keys": []}]
    if solution:
        sections.append({"key": "solution", "html": "<p>Авторское решение.</p>", "asset_keys": []})
    return {"normalized_content": {"format": "teacherhelper-normalized", "schema_version": 3, "assets": [], "sections": sections}}


@pytest.mark.parametrize("size,total,answer", [(12, 400, "12"), (12, 300, "7"), (8, 300, "9")])
def test_audited_group_variants(size, total, answer):
    value = context(size=size, total=total)
    before = deepcopy(value)
    plan = build_context_repair_plan(value)
    assert plan.answer == answer
    assert len(plan.transformations) == 2
    assert value == before
    assert plan.condition_html == before["normalized_content"]["sections"][0]["html"]


def test_exact_byte_boundary_and_zero_extra():
    plan = build_context_repair_plan(context(size=8, length=16, total=120))
    assert plan.answer == "0"
    assert r"\frac{48}{8}=6" in plan.solution_html
    assert r"\left\lceil" not in plan.solution_html
    assert 'округляем' not in plan.solution_html


@pytest.mark.parametrize("size,length,decimal,rounded", [
    (12, 15, "7{,}5", 8), (12, 3, "1{,}5", 2), (8, 15, "5{,}625", 6),
])
def test_fractional_byte_count_is_shown_before_rounding(size, length, decimal, rounded):
    plan = build_context_repair_plan(context(size=size, length=length))
    conversion = rf"\frac{{{(size - 1).bit_length() * length}}}{{8}}={decimal}"
    rounding = rf"\left\lceil {decimal}\right\rceil={rounded}"
    assert conversion in plan.solution_html
    assert rounding in plan.solution_html
    assert plan.solution_html.index(conversion) < plan.solution_html.index(rounding)
    assert 'до кратного восьми' not in plan.solution_html


def test_existing_solution_is_rewritten_with_latex_and_then_converges():
    value = context(solution=True)
    value["normalized_content"]["sections"].append({"key": "answer", "html": '<p><span data-effect="spaced">12</span></p>'})
    plan = build_context_repair_plan(value)
    assert len(plan.transformations) == 1
    assert plan.transformations[0]["transformation_target_id"] == "section:solution"
    assert plan.transformations[0]["value"]["html"] == plan.solution_html
    assert '<span data-inline-latex="N"></span>' in plan.solution_html
    assert '<span data-inline-latex="2^N"></span>' in plan.solution_html
    assert r'20\cdot(8+x)=400' in plan.solution_html
    assert '<sup>' not in plan.solution_html
    value["normalized_content"]["sections"][1]["html"] = plan.solution_html
    assert not build_context_repair_plan(value).transformations


@pytest.mark.parametrize("changes", [{"total": 301}, {"total": 100}, {"size": 1}])
def test_inconsistent_allocations_fail_closed(changes):
    with pytest.raises(UnsupportedCondition):
        build_context_repair_plan(context(**changes))


@pytest.mark.parametrize("replacement", ["неодинаковым", "одинаковым, но не минимальным"])
def test_changed_encoding_contract_fails_closed(replacement):
    value = context()
    section = value["normalized_content"]["sections"][0]
    section["html"] = section["html"].replace("одинаковым и минимально возможным", replacement)
    with pytest.raises(UnsupportedCondition):
        build_context_repair_plan(value)


def test_assets_and_incorrect_alphabet_fail_closed():
    value = context()
    value["normalized_content"]["assets"] = [{"asset_id": "unexpected"}]
    with pytest.raises(UnsupportedCondition):
        build_context_repair_plan(value)
    value = context()
    value["normalized_content"]["sections"][0]["html"] = value["normalized_content"]["sections"][0]["html"].replace("12-", "11-")
    with pytest.raises(UnsupportedCondition):
        build_context_repair_plan(value)


def test_registration_uses_exact_catalog_and_parent():
    profile = get_group_profile("9364")
    assert profile.catalog_snapshot_id == "4b8ce070-551c-4697-9b42-11c2617966d8"
    assert profile.source_group_id == "88cfe7e0-7597-46ad-b077-de5bf6b4d812"
    handler = get_handler(profile.content_rule_key)
    handler.validate()
    assert handler.expected_parent_id is None
    assert handler.parent_from_group_listing
    assert not handler.requires_parent_condition_asset
    assert handler.verify_content_readback
    assert profile.existing_solution_policy == "rewrite"
