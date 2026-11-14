"""Keep two-case parent signs and base comparison, with original asset roles."""

import hashlib
import json
from pathlib import Path

import sympy as sp
from bs4 import BeautifulSoup

from ..probability.common import UnsupportedCondition, line
from .inequality_plan import repair
from .logarithm_product_cancellation_proof import logarithm
from .logarithm_rationalization_proof import choices, system
from .logarithm_sign_cases import base_order, product_cases, side
from .rational_inequality_figures import read_formula
from .rational_inequality_parser import X
from .rational_inequality_proof import RELATION
from .rational_substitution_preimages import comparison

SOURCES = json.loads(
    (
        Path(__file__).parent / "assets/logarithmic-inequalities/sign-cases.json"
    ).read_text()
)


def log(atom):
    return logarithm(atom.base, sp.latex(atom.argument))


def domain_text(a):
    rows = []
    for atom in a.atoms:
        rows.extend([sp.latex(atom.base) + ">0", sp.latex(atom.base) + r"\ne1"])
        if atom.argument.has(X):
            rows.append(sp.latex(atom.argument) + ">0")
    rows.extend("x\\ne" + sp.latex(p) for p in a.poles)
    return (
        "<p>Найдём область допустимых значений: основания и аргументы положительны, основания отличны от единицы, исходные знаменатели не равны нулю.</p>"
        + system(list(dict.fromkeys(rows)))
        + line(choices("x", a.domain))
    )


def fixed_sign_text(a):
    atom = a.atoms[a.fixed_index]
    sign = ">" if a.fixed_sign > 0 else "<"
    html = "<p>Определим знак одного множителя на всей области допустимых значений. Логарифм положителен, когда основание и аргумент находятся по одну сторону от единицы, и отрицателен, когда они по разные стороны:</p>"
    for region in a.sign_regions:
        html += system(
            [
                choices("x", region.domain),
                sp.latex(atom.base) + (">1" if region.increasing else "<1"),
                sp.latex(atom.argument) + (">1" if region.argument_above else "<1"),
            ]
        )
    html += line(log(atom) + sign + "0")
    html += (
        "<p>Поэтому произведение не превосходит нуля тогда и только тогда, когда другой множитель имеет "
        + ("неположительный" if a.fixed_sign > 0 else "неотрицательный")
        + " знак:</p>"
    )
    return html + line(log(a.varying) + RELATION[a.target] + "0")


def render_product(a):
    html = domain_text(a)
    if a.domain == sp.EmptySet:
        return html
    html += fixed_sign_text(a)
    for index, case in enumerate(a.cases, 1):
        html += (
            "<p>"
            + ("Первый" if index == 1 else "Второй")
            + " случай: "
            + (
                "основание больше единицы."
                if case.increasing
                else "основание между нулём и единицей."
            )
            + "</p>"
        )
        base = sp.latex(a.varying.base)
        html += line(base + ">1" if case.increasing else "0<" + base + "<1")
        html += line(choices("x", case.domain))
        html += (
            "<p>На этом множестве используем "
            + ("возрастание" if case.increasing else "убывание")
            + " логарифма и учитываем исходные ограничения:</p>"
        )
        html += system(
            [log(a.varying) + RELATION[a.target] + "0", choices("x", case.domain)]
        )
        html += system(
            [
                sp.latex(a.varying.argument) + ">0",
                sp.latex(a.varying.argument) + RELATION[case.operator] + "1",
                choices("x", case.domain),
            ]
        )
        html += line(choices("x", case.stage.solution))
        html += line(choices("x", case.solution))
    return (
        html + "<p>Объединим найденные промежутки:</p>" + line(choices("x", a.solution))
    )


def cancel_common_x(first, second, scope):
    if scope.is_subset(comparison(X, ">").solution) is not True:
        return ""
    u, v = sp.cancel(first.base / X), sp.cancel(second.base / X)
    n, d = sp.fraction(u)
    m, e = sp.fraction(v)
    if (
        n != 1
        or m != 1
        or any(scope.is_subset(comparison(q, ">").solution) is not True for q in (d, e))
    ):
        return ""
    html = "<p>На этом множестве x положителен. Сократим общий положительный множитель; знаменатели оставшихся дробей также положительны:</p>"
    html += line(sp.latex(u) + r"\ge " + sp.latex(v))
    return (
        html
        + line(sp.latex(d) + r"\le " + sp.latex(e))
        + line(choices("x", comparison(e - d, ">=").solution))
    )


def order_same_sign(a, case):
    first, second = a.atoms
    html = (
        "<p>При двух основаниях больше единицы и общем аргументе больше единицы меньшему логарифму соответствует большее основание:</p>"
        if case.left_increasing
        else "<p>Оба основания между нулём и единицей. По формуле смены основания получаются обратные величины одного знака, поэтому сравнение также сводится к обратному порядку оснований:</p>"
    )
    if not case.left_increasing:
        html += line(
            log(first)
            + r"=\frac{1}{"
            + logarithm(a.argument, sp.latex(first.base))
            + "}"
        )
        html += line(
            log(second)
            + r"=\frac{1}{"
            + logarithm(a.argument, sp.latex(second.base))
            + "}"
        )
    html += line(sp.latex(first.base) + r"\ge " + sp.latex(second.base))
    cancelled = cancel_common_x(first, second, case.domain)
    if cancelled:
        html += cancelled
    else:
        html += line(sp.latex(case.stage.original) + r"\ge0")
        if case.stage.original != case.stage.expression:
            html += line(
                sp.latex(case.stage.expression)
                + RELATION[case.stage.sign_operator]
                + "0"
            )
        html += line(choices("x", case.stage.solution))
    html += "<p>Сохраняя рассматриваемую область, получаем:</p>"
    return html + line(choices("x", case.solution))


def order_note():
    return (
        "<p>Примечание. Использованы свойства логарифмов: при основаниях и аргументе больше единицы логарифмы положительны, а порядок оснований противоположен порядку логарифмов.</p>"
        + line(r"a,b,c>1:\quad\log_a c\le\log_b c\iff a\ge b")
    )


def render_order(a):
    html = domain_text(a)
    if a.domain == sp.EmptySet:
        return html
    first, second = a.atoms
    if a.domain.is_subset(side(first.base, True)) is True:
        html += "<p>На области допустимых значений первое основание больше единицы, а значит, левая часть положительна:</p>"
        html += line(
            sp.latex(first.base) + "=1+" + sp.latex(sp.cancel(first.base - 1)) + ">1"
        )
        html += line(log(first) + ">0")
        html += "<p>Правая часть не меньше положительной левой части, поэтому тоже положительна. При аргументе больше единицы это требует второго основания больше единицы:</p>"
        html += line(
            log(second)
            + ">0"
            + r"\quad\Longrightarrow\quad "
            + sp.latex(second.base)
            + ">1"
        )
        case = next(
            (c for c in a.cases if c.left_increasing and c.right_increasing), None
        )
        if case is None:
            return (
                html
                + "<p>Эти условия несовместны с областью допустимых значений. Решений нет.</p>"
                + order_note()
            )
        html += line(choices("x", case.domain)) + order_same_sign(a, case)
        return html + order_note()
    else:
        html += "<p>Рассмотрим расположение обоих оснований относительно единицы:</p>"
        for case in a.cases:
            html += system(
                [
                    sp.latex(first.base) + (">1" if case.left_increasing else "<1"),
                    sp.latex(second.base) + (">1" if case.right_increasing else "<1"),
                    choices("x", case.domain),
                ]
            )
            if case.stage is not None:
                html += order_same_sign(a, case)
            elif not case.left_increasing:
                html += (
                    "<p>Левая часть отрицательна, правая положительна. Неравенство верно на всём этом множестве:</p>"
                    + line(choices("x", case.solution))
                )
            else:
                html += "<p>Левая часть положительна, правая отрицательна. На этом множестве решений нет.</p>"
    return (
        html
        + "<p>Объединяя допустимые значения, получаем:</p>"
        + line(choices("x", a.solution))
        + order_note()
    )


def validate_assets(content, condition, a, method):
    assets = content.get("assets") or ()
    if not assets:
        return
    if (
        method != "variable_log_product_cases"
        or condition.get("asset_keys")
        or BeautifulSoup(condition["html"], "html.parser").find("img")
    ):
        raise UnsupportedCondition("unreviewed condition figures cannot be discarded")
    signature = [str(value) for atom in a.atoms for value in (atom.base, atom.argument)]
    for asset in assets:
        reviewed = SOURCES["solution_assets"].get(asset.get("asset_id"))
        if (
            reviewed is None
            or reviewed["signature"] != signature
            or asset.get("asset_key") != reviewed["asset_key"]
            or asset.get("kind") != "ordinary_image"
            or str(asset.get("asset_id")) in condition["html"]
        ):
            raise UnsupportedCondition(
                "only the reviewed alternative child solution asset may remain unused by the parent cases"
            )


def build_context_repair_plan(
    context, *, parent_solution_html="", method="variable_log_product_cases"
):
    if (
        SOURCES["parents"].get(
            hashlib.sha256(parent_solution_html.encode()).hexdigest()
        )
        != method
    ):
        raise UnsupportedCondition(
            "the complete reviewed logarithm sign-case parent is required"
        )
    (content, condition, answer, solution), formula = read_formula(context)
    if method == "variable_log_product_cases":
        a = product_cases(formula)
        html = render_product(a)
    elif method == "variable_log_base_order":
        a = base_order(formula)
        html = render_order(a)
    else:
        raise UnsupportedCondition("unknown logarithm sign-case method")
    validate_assets(content, condition, a, method)
    return repair(condition, answer, solution, a.answer, html)
