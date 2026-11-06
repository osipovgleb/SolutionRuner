"""Build identical answer and solution transformations for shared inequality planners."""

from ..word_problems.common import RepairPlan, rewrite


def repair(
    condition, answer_section, solution, answer, html, *, keys=(), asset_changes=()
):
    answer_html = '<p><span data-inline-latex="' + answer + '"></span></p>'
    changes = list(asset_changes)
    if answer_section is None or answer_section.get("html") != answer_html:
        changes.append(rewrite(answer_section, "answer", "Ответ", answer_html))
    if (
        solution is None
        or solution.get("html") != html
        or tuple(solution.get("asset_keys") or ()) != keys
    ):
        change = rewrite(solution, "solution", "Решение", html)
        change["value"]["asset_keys"] = list(keys)
        changes.append(change)
    return RepairPlan(answer, condition["html"], html, tuple(changes))
