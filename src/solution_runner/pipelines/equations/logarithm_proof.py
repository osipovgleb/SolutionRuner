"""Show logarithm identities in the order of the source calculation."""

import sympy as sp

from ..probability.common import UnsupportedCondition, line
from . import logarithm_arithmetic as arithmetic
from .logarithm_parser import Node, combined


def _log(base, argument):
    return Node(
        arithmetic.log_ratio(base.value, argument.value),
        rf"\log_{{{base.text}}}({argument.text})",
        "log",
        (base, argument),
    )


def as_log(node):
    if node.kind == "log":
        return node
    if node.kind == "divide":
        a, b = node.children
        if a.kind == b.kind == "log" and a.children[0].value == b.children[0].value:
            return _log(b.children[1], a.children[1])
    if node.kind in ("add", "subtract"):
        a, b = (as_log(c) for c in node.children)
        if a and b and a.children[0].value == b.children[0].value:
            argument = combined(
                "multiply" if node.kind == "add" else "divide",
                a.children[1],
                b.children[1],
            )
            return _log(a.children[0], argument)
    return None


def _direct_log(node):
    base, argument = node.children
    if node.value.is_Rational:
        return [
            rf"({base.text})^{{{sp.latex(node.value)}}}={argument.text}",
            node.text + "=" + sp.latex(node.value),
        ]
    powers = argument.value.as_powers_dict()
    terms = []
    for prime, exponent in powers.items():
        if prime.is_Rational is not True:
            return []
        for p, factors in arithmetic.factor_base(prime).items():
            coefficient = exponent * sum(t.value for t in factors)
            label = rf"\log_{{{base.text}}}{p}"
            terms.append(
                (
                    ""
                    if coefficient == 1
                    else "-"
                    if coefficient == -1
                    else "(" + sp.latex(coefficient) + ")"
                )
                + label
            )
    return [node.text + "=" + "+".join(terms).replace("+-", "-")]


def _power_steps(node):
    base, exponent = node.children
    steps = proof(exponent)
    if base.kind == "power":
        inner, first_exponent = base.children
        merged = combined("multiply", first_exponent, exponent)
        steps += [node.text + "=(" + inner.text + ")^{" + merged.text + "}"]
        steps += proof(merged)
    elif exponent.kind == "log":
        log_base, argument = exponent.children
        ratio = arithmetic.log_ratio(log_base.value, base.value)
        if ratio.is_Rational:
            steps += [base.text + "=(" + log_base.text + ")^{" + sp.latex(ratio) + "}"]
            steps += [node.text + "=(" + argument.text + ")^{" + sp.latex(ratio) + "}"]
    elif exponent.kind in ("add", "multiply"):
        a, b = exponent.children
        if exponent.kind == "add":
            steps += [
                node.text
                + "=("
                + base.text
                + ")^{"
                + a.text
                + r"}\cdot("
                + base.text
                + ")^{"
                + b.text
                + "}"
            ]
        else:
            steps += [
                node.text + "=((" + base.text + ")^{" + b.text + "})^{" + a.text + "}"
            ]
    if node.value.is_Rational:
        steps += [node.text + "=" + sp.latex(node.value)]
    return steps


def proof(node):
    match node.kind:
        case "scalar":
            return []
        case "log":
            return proof(node.children[1]) + _direct_log(node)
        case "power":
            return _power_steps(node)
        case "divide":
            a, b = node.children
            if (
                a.kind == b.kind == "power"
                and a.children[0].value == b.children[0].value
            ):
                exponent = combined("subtract", a.children[1], b.children[1])
                return (
                    [
                        node.text
                        + "=("
                        + a.children[0].text
                        + ")^{"
                        + exponent.text
                        + "}"
                    ]
                    + proof(exponent)
                    + [node.text + "=" + sp.latex(node.value)]
                )
    equivalent = as_log(node)
    if equivalent:
        return [node.text + "=" + equivalent.text] + proof(equivalent)
    if node.kind == "multiply":
        a, b = node.children
        if a.kind == b.kind == "log":
            first = _log(a.children[0], b.children[1])
            second = _log(b.children[0], a.children[1])
            return (
                [node.text + "=" + first.text + r"\cdot" + second.text]
                + proof(first)
                + proof(second)
                + (
                    [node.text + "=" + sp.latex(node.value)]
                    if node.value.is_Rational
                    else []
                )
            )
    steps = [step for child in node.children for step in proof(child)]
    if node.value.is_Rational:
        operands = [
            sp.latex(c.value) if c.value.is_Rational else c.text for c in node.children
        ]
        if node.kind in ("multiply", "add", "subtract"):
            symbol = {"multiply": r"\cdot", "add": "+", "subtract": "-"}[node.kind]
            steps.append(
                "("
                + operands[0]
                + ")"
                + symbol
                + "("
                + operands[1]
                + ")="
                + sp.latex(node.value)
            )
        elif node.kind == "divide":
            steps.append(
                r"\frac{"
                + operands[0]
                + "}{"
                + operands[1]
                + "}="
                + sp.latex(node.value)
            )
        else:
            steps.append(node.text + "=" + sp.latex(node.value))
    return steps


def _complements(node):
    if node.kind != "multiply" or any(c.kind != "subtract" for c in node.children):
        raise UnsupportedCondition(
            "two source methods require a product of logarithmic complements"
        )
    left, right = node.children
    one, first = left.children
    other_one, second = right.children
    if (
        one.value != 1
        or other_one.value != 1
        or first.kind != "log"
        or second.kind != "log"
    ):
        raise UnsupportedCondition("unsupported logarithmic complements")
    a, c = first.children
    b, d = second.children
    if c.value != d.value or c.value != a.value * b.value or node.value != 1:
        raise UnsupportedCondition(
            "the complementary logarithm product relation is missing"
        )
    A, B, C = a.text, b.text, c.text
    first_steps = [
        node.text + rf"=(1-\log_{{{A}}}(({A})({B})))(1-\log_{{{B}}}(({A})({B})))",
        rf"=(1-1-\log_{{{A}}}{B})(1-\log_{{{B}}}{A}-1)",
        rf"=(-\log_{{{A}}}{B})(-\log_{{{B}}}{A})=1",
    ]
    second_steps = [
        rf"(\log_{{{A}}}{A}-\log_{{{A}}}{C})(\log_{{{B}}}{B}-\log_{{{B}}}{C})",
        rf"=\log_{{{A}}}\frac{{{A}}}{{{C}}}\cdot\log_{{{B}}}\frac{{{B}}}{{{C}}}",
        rf"=\log_{{{A}}}\frac{{1}}{{{B}}}\cdot\log_{{{B}}}\frac{{1}}{{{A}}}",
        rf"=\log_{{{A}}}\frac{{1}}{{{A}}}\cdot\log_{{{B}}}\frac{{1}}{{{B}}}=(-1)(-1)=1",
    ]
    return first_steps, second_steps


def _fraction_sum(node):
    if node.kind != "divide":
        raise UnsupportedCondition("two source methods require a logarithmic fraction")
    numerator, denominator = node.children
    if numerator.kind != "log" or denominator.kind != "add":
        raise UnsupportedCondition("unsupported two-method logarithmic fraction")
    k, tail = denominator.children
    if tail.kind != "log" or not k.value.is_Integer:
        raise UnsupportedCondition(
            "the logarithmic denominator must be an integer plus a logarithm"
        )
    base, argument = numerator.children
    if (
        tail.children[0].value != base.value
        or argument.value != base.value**k.value * tail.children[1].value
        or node.value != 1
    ):
        raise UnsupportedCondition(
            "the numerator and denominator logarithms do not match"
        )
    A, C, K, D = base.text, argument.text, k.text, tail.children[1].text
    factor = sp.latex(base.value**k.value)
    first = [
        rf"\log_{{{A}}}{C}=\log_{{{A}}}({factor}\cdot({D}))",
        rf"=\log_{{{A}}}{factor}+\log_{{{A}}}{D}={K}+\log_{{{A}}}{D}",
        node.text + rf"=\frac{{{K}+\log_{{{A}}}{D}}}{{{K}+\log_{{{A}}}{D}}}=1",
    ]
    second = [
        rf"{K}=\log_{{{A}}}{factor}",
        rf"{K}+\log_{{{A}}}{D}=\log_{{{A}}}{factor}+\log_{{{A}}}{D}=\log_{{{A}}}{C}",
        node.text + rf"=\frac{{\log_{{{A}}}{C}}}{{\log_{{{A}}}{C}}}=1",
    ]
    return first, second


def render(node, *, two_methods=None, product_proof=False):
    html = "<p>Используем свойства логарифмов. Аргументы положительны, основания положительны и отличны от единицы; знаменатели ненулевые.</p>"
    html += line(r"\log_a(uv)=\log_a u+\log_a v,\quad \log_a\frac uv=\log_a u-\log_a v")
    html += line(r"\log_a(u^r)=r\log_a u,\quad a^{\log_a u}=u")
    if two_methods:
        first, second = (
            _complements(node) if two_methods == "complements" else _fraction_sum(node)
        )
        html += "<p>Первый способ. Разложим логарифм произведения:</p>"
        html += "".join(line(s) for s in first)
        html += (
            "<p>Второй способ. Объединим разности или суммы логарифмов и сократим:</p>"
        )
        return html + "".join(line(s) for s in second)
    html += "<p>Применим свойства к данному выражению и последовательно вычислим:</p>"
    if any(
        n.kind == "multiply" and all(c.kind == "log" for c in n.children)
        for n in walk(node)
    ):
        html += line(r"\log_a b\cdot\log_c d=\log_a d\cdot\log_c b")
    if any(
        n.kind == "divide" and all(c.kind == "log" for c in n.children)
        for n in walk(node)
    ):
        html += line(r"\frac{\log_a b}{\log_a c}=\log_c b")
    html += "".join(line(s) for s in dict.fromkeys(proof(node)))
    if product_proof:
        html += "<p>Обоснуем использованную формулу переходом к общему основанию:</p>"
        html += line(
            r"\log_a b\cdot\log_c d=\frac{\ln b\ln d}{\ln a\ln c}=\log_a d\cdot\log_c b"
        )
    return html


def walk(node):
    yield node
    for child in node.children:
        yield from walk(child)
