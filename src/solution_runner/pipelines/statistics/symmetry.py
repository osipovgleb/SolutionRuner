"""Symmetry of a finite law, preserving the compatible source plot."""

from dataclasses import replace
from fractions import Fraction
from html import escape

from solution_runner.pipelines.word_problems.common import rewrite

from .common import UnsupportedCondition, finish, fmt, line, read, result
from .tables import _rows, expectation

_SOURCE = "e61663d3-e855-46a9-9e3c-bc35f29cd63d"
_VALUES = (1, 2, 4, 6, 8, 9)
_WEIGHTS = tuple(map(Fraction, ("0.012", "0.152", "0.336", "0.336", "0.152", "0.012")))
_ALT = "Симметричное распределение вероятностей"
_TEXT = "Найдите математическое ожидание случайной величины X, имеющей следующее распределение вероятностей:"


def _input(context):
    content = context.get("normalized_content") or {}
    clean = {**context, "normalized_content": {**content, "assets": []}}
    condition, answer, solution, text, tables = read(clean)
    if text != _TEXT:
        raise UnsupportedCondition(
            "unsupported complete symmetric-distribution condition"
        )
    xs, ps = _rows(tables, ("Значения X", "Вероятность"))
    mean, _ = expectation(xs, ps)
    pairs = sorted(zip(xs, ps))
    center = (pairs[0][0] + pairs[-1][0]) / 2
    if len(set(xs)) != len(xs) or any(
        x + y != 2 * center or p != q for (x, p), (y, q) in zip(pairs, reversed(pairs))
    ):
        raise UnsupportedCondition("the law is not symmetric around one center")
    if tuple(x for x, p in pairs) != _VALUES or tuple(p for x, p in pairs) != _WEIGHTS:
        raise UnsupportedCondition(
            "a different symmetric law needs its own compatible diagram"
        )
    if center != mean:
        raise UnsupportedCondition("the symmetry center disagrees with the expectation")
    return content, condition, answer, solution, pairs, center


def required_assets(context):
    _input(context)
    return ({"source_asset_id": _SOURCE, "section_id": "solution:1", "alt_text": _ALT},)


def build_context_repair_plan(context):
    content, condition, answer_section, solution, pairs, center = _input(context)
    asset = next(
        (a for a in content.get("assets", []) if a.get("asset_id") == _SOURCE), None
    )
    if asset is None:
        raise UnsupportedCondition("the compatible source probability plot is required")
    key = asset["asset_key"]
    image = f'<center><img alt="{_ALT}" data-asset-key="{escape(key, quote=True)}" data-asset-id="{_SOURCE}" src="/assets/{_SOURCE}"/></center>'
    html = (
        "<p>Из таблицы и рисунка видно, что равные вероятности соответствуют значениям, одинаково удалённым от одной точки:</p>"
        + image
    )
    html += line(
        rf"c=\frac{{{fmt(pairs[0][0])}+{fmt(pairs[-1][0])}}}{{2}}={fmt(center)}"
    )
    html += (
        "<p>В каждой симметричной паре отклонения от c противоположны, а вероятности равны. Поэтому их вклады в ожидание отклонения взаимно уничтожаются:</p>"
        + line(r"E(X-c)=0")
        + line(r"E(X)-c=0")
    )
    html += "<p>Следовательно, математическое ожидание совпадает с центром симметрии. Сам центр не обязан быть возможным значением величины.</p>"
    answer, html = result(center, html)
    repair = finish(condition, answer_section, solution, answer, html)
    changes = list(repair.transformations)
    if not any(
        t["transformation_target_id"].startswith("section:solution") for t in changes
    ) and (solution or {}).get("asset_keys") != [key]:
        changes.append(rewrite(solution, "solution", "Решение", html))
    for t in changes:
        if t["transformation_target_id"].startswith("section:solution"):
            t["value"]["asset_keys"] = [key]
    return replace(repair, transformations=tuple(changes))
