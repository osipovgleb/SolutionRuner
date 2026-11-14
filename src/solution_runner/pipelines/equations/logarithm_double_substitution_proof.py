"""Retain the parent t-then-z substitution, interval method and final note."""

import hashlib
import json
from pathlib import Path

import sympy as sp
from bs4 import BeautifulSoup

from ..probability.common import UnsupportedCondition, line
from .inequality_plan import repair
from .logarithm_double_substitution import analyze
from .logarithm_product_cancellation_proof import logarithm
from .logarithm_rationalization_proof import choices
from .rational_inequality_figures import read_formula
from .rational_inequality_parser import X

SOURCES = json.loads(
    (
        Path(__file__).parent
        / "assets/logarithmic-inequalities/double-substitution.json"
    ).read_text()
)


def validate_assets(content, condition, a):
    if condition.get("asset_keys") or BeautifulSoup(
        condition["html"], "html.parser"
    ).find("img"):
        raise UnsupportedCondition(
            "the reviewed double-substitution condition has no figures"
        )
    for asset in content.get("assets", ()):
        entry = SOURCES["solution_assets"].get(asset.get("asset_id"))
        if (
            entry is None
            or entry["base"] != str(a.logarithm.base)
            or entry["expression"] != str(a.logarithm.stage.original)
            or asset.get("asset_key") != entry["asset_key"]
            or asset.get("kind") != "ordinary_image"
            or asset.get("url") != "/assets/" + asset["asset_id"]
            or asset["asset_id"] in condition["html"]
        ):
            raise UnsupportedCondition(
                "only the reviewed alternative child diagram may remain unused by the parent method"
            )


def render(a):
    t, z = sp.symbols("t z", real=True)
    q = a.inner.subs(X, t)
    grouped = sp.Add(
        sp.Pow(q, 2, evaluate=False),
        sp.Mul(a.linear, q, evaluate=False),
        a.constant,
        evaluate=False,
    )
    log = logarithm(a.logarithm.base, "x")
    html = "<p>Область определения: x положителен. Пусть:</p>" + line("x>0")
    html += line("t=" + log)
    html += "<p>Тогда исходное неравенство примет вид:</p>" + line(
        sp.latex(grouped) + "<0"
    )
    html += "<p>Пусть теперь:</p>" + line("z=" + sp.latex(q))
    html += line(sp.latex(a.outer_stage.original.subs(X, z)) + "<0")
    html += line(sp.latex(sp.factor(a.outer_stage.original).subs(X, z)) + "<0")
    html += "<p>Вернёмся к переменной t, получим целое неравенство и решим его методом интервалов:</p>"
    quadratics = sp.Mul(*(q - root for root in a.outer_stage.zeros), evaluate=False)
    factors = sp.Mul(
        *(sp.factor(q - root) for root in a.outer_stage.zeros), evaluate=False
    )
    html += line(sp.latex(quadratics) + "<0")
    html += line(sp.latex(factors) + "<0")
    html += line(choices("t", a.logarithm.stage.solution))
    html += "<p>Вернёмся к переменной x. Логарифм по основанию больше единицы возрастает; для каждого промежутка получаем:</p>"
    for source, image in a.logarithm.images:
        html += line(choices(log, source))
        html += line(choices("x", image))
    return html + SOURCES["note"]


def build_context_repair_plan(context, *, parent_solution_html=""):
    if (
        hashlib.sha256(parent_solution_html.encode()).hexdigest()
        not in SOURCES["parents"]
    ):
        raise UnsupportedCondition(
            "the complete reviewed double-substitution parent is required"
        )
    (content, condition, answer, solution), formula = read_formula(context)
    a = analyze(formula)
    validate_assets(content, condition, a)
    return repair(condition, answer, solution, a.answer, render(a))
