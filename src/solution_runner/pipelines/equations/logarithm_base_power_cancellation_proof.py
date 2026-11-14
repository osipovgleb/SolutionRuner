"""Keep the parent's log-property reduction, base cases and supplemental rationalization."""

import hashlib
import json
from pathlib import Path

import sympy as sp

from ..core.condition_transcriptions import transcribe_condition
from ..probability.common import UnsupportedCondition, line
from ..word_problems.common import rewrite
from .expression_repair import with_condition_repair
from .inequality_plan import repair
from .logarithm_base_power_cancellation import analyze
from .logarithm_product_cancellation_proof import logarithm
from .logarithm_rationalization_proof import choices, system
from .rational_inequality_figures import read_formula
from .rational_inequality_proof import RELATION
from .single_log_three_methods_proof import case_proof, product_proof

SOURCES = json.loads(
    (
        Path(__file__).parent
        / "assets/logarithmic-inequalities/base-power-cancellation.json"
    ).read_text()
)


def reduction(a):
    B, H = a.base, a.linear
    source = logarithm(B, sp.latex(sp.factor(a.argument.value)))
    reduced = logarithm(B, sp.latex(H))
    factored = sp.Mul(
        sp.Pow(B, a.bound, evaluate=False),
        sp.Pow(H, a.sign, evaluate=False),
        evaluate=False,
    )
    html = "<p>Преобразуем неравенство, используя свойства логарифма на исходной области определения:</p>"
    html += system(
        [
            sp.latex(B) + ">0",
            sp.latex(B) + r"\ne1",
            sp.latex(sp.factor(a.argument.value)) + ">0",
        ]
    )
    html += line(choices("x", a.logarithm.domain))
    html += "<p>Выделим степень основания. На исходной области она положительна, поэтому оставшийся множитель также положителен:</p>"
    html += line(sp.latex(sp.factor(a.argument.value)) + "=" + sp.latex(factored))
    html += line(sp.latex(H) + ">0")
    html += line(
        source + "=" + sp.latex(a.bound) + ("+" if a.sign == 1 else "-") + reduced
    )
    html += line(
        source
        + RELATION[a.operator]
        + sp.latex(a.bound)
        + r"\iff "
        + reduced
        + RELATION[a.logarithm.operator]
        + "0"
    )
    return html


def build_context_repair_plan(context, *, parent_solution_html=""):
    if (
        hashlib.sha256(parent_solution_html.encode()).hexdigest()
        not in SOURCES["parents"]
    ):
        raise UnsupportedCondition(
            "the complete reviewed base-power cancellation parent is required"
        )
    (_, original, _, _), _ = read_formula(context)
    prepared, fixed = transcribe_condition(
        context, original, SOURCES["condition_transcriptions"], validate=read_formula
    )
    (content, condition, answer, solution), formula = read_formula(prepared)
    if content.get("assets") or condition.get("asset_keys"):
        raise UnsupportedCondition(
            "the reviewed base-power cancellation group has no figures"
        )
    a = analyze(formula)
    html = '<section data-content-kind="solution" data-solution-title="Решение">'
    html += (
        reduction(a)
        + case_proof(a.logarithm, above_first=False, heading=False)
        + "</section>"
    )
    html += '<section data-content-kind="solution" data-solution-title="Приведём другое решение.">'
    html += reduction(a) + product_proof(a.logarithm, "") + "</section>"
    plan = repair(condition, answer, solution, a.answer, html)
    return with_condition_repair(
        plan,
        rewrite(original, "condition", "Условие", fixed) if fixed is not None else None,
    )
