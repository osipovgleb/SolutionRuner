"""Reduce reviewed identities, keep zero factors and select exact periodic roots."""

from dataclasses import dataclass
from functools import cmp_to_key, lru_cache

import sympy as sp
from bs4 import BeautifulSoup

from ..word_problems.common import UnsupportedCondition
from ..word_problems.math_common import primitive
from .exam_exponential import X
from .exam_logarithmic_algebra import roots
from .exam_scalar import compare
from .power_arithmetic import clean
from .trig_angles import C as NUMERIC_C
from .trig_angles import S as NUMERIC_S
from .trig_symbolic_parser import SymbolicTrigonometricParser, compile_atoms

S, C = sp.symbols("s c", real=True)


@dataclass(frozen=True)
class Branch:
    variable: sp.Symbol
    polynomial: sp.Expr
    candidates: tuple
    values: tuple
    residues: tuple


@dataclass(frozen=True)
class Analysis:
    original: str
    raw: sp.Expr
    identities: tuple
    reduced: sp.Expr
    branches: tuple
    residues: tuple
    series: tuple
    selected: tuple
    selections: tuple
    interval: str
    bounds: tuple
    preferred: sp.Symbol
    square: bool
    alternating: bool
    image_position: str


def compile_equation(formula):
    text = clean(formula)
    if text.count("=") != 1:
        raise UnsupportedCondition("one complete trigonometric equation is required")
    atoms = {}
    denominators = []
    values = []
    for side in text.split("="):
        parser = SymbolicTrigonometricParser(
            side.replace("x", r"\alpha"), atoms, denominators
        )
        values.append(parser.parse().value)
    base, _, compiled, poles = compile_atoms(parser)
    if (
        base != 1
        or poles
        or any(a.function not in ("sin", "cos") for a in atoms.values())
    ):
        raise UnsupportedCondition(
            "reviewed sine and cosine equations have one base angle and no original denominators"
        )
    raw = sp.expand(
        (values[0] - values[1])
        .xreplace(compiled)
        .xreplace({NUMERIC_S: S, NUMERIC_C: C})
    )
    if not raw.is_polynomial(S, C) or sp.Poly(raw, S, C).total_degree() > 4 or raw == 0:
        raise UnsupportedCondition(
            "a nonzero polynomial of sine and cosine of degree at most four is required"
        )
    identities = tuple(
        dict.fromkeys(
            (
                atom.text.replace(r"\alpha", "x"),
                compiled[symbol].xreplace({NUMERIC_S: S, NUMERIC_C: C}),
            )
            for symbol, atom in atoms.items()
        )
    )
    return raw, identities


@lru_cache(maxsize=128)
def table(variable, value):
    f = sp.sin if variable == S else sp.cos
    result = tuple(
        sp.Rational(i, 12)
        for i in range(24)
        if sp.simplify(f(sp.pi * i / 12) - value) == 0
    )
    if not result:
        raise UnsupportedCondition("a complete reviewed exact angle table is required")
    return result


def periodic(residues):
    residues = set(residues)
    if not residues:
        return ()
    shifts = sorted(
        {
            sp.Integer(2),
            *((b - a) % 2 for a in residues for b in residues if (b - a) % 2),
        }
    )
    period = next(p for p in shifts if {(q + p) % 2 for q in residues} == residues)
    return tuple((q, period) for q in sorted({q % period for q in residues}))


def solve_branches(raw, preferred):
    other = S if preferred == C else C
    reduced = sp.expand(sp.rem(raw, S * S + C * C - 1, other))
    if not reduced.has(other):
        expressions = [reduced]
    else:
        _, factors = sp.factor_list(raw, S, C)
        expressions = [p for p, _ in factors]
    branches = []
    for expression in expressions:
        variables = expression.free_symbols & {S, C}
        if len(variables) != 1:
            raise UnsupportedCondition(
                "each factor must reduce to one sine or cosine without division"
            )
        variable = variables.pop()
        p = primitive(expression, (variable,))
        values = roots(p.subs(variable, X))
        accepted = tuple(
            v
            for v in values
            if compare(v, -sp.Integer(1)) >= 0 and compare(v, sp.Integer(1)) <= 0
        )
        residues = tuple(sorted({q for v in accepted for q in table(variable, v)}))
        branches.append(Branch(variable, p, values, accepted, residues))
    return reduced, tuple(branches)


def parent_style(parent_html):
    import re

    soup = BeautifulSoup(parent_html, "html.parser")
    text = soup.get_text(" ", strip=True).replace("\xad", "").lower()
    if "окружност" not in text or any(
        s in text for s in ("другое решение", "еще одно решение")
    ):
        raise UnsupportedCondition(
            "one reviewed parent method with circle selection is required"
        )
    formulas = [
        "".join(s["data-inline-latex"].split())
        for s in soup.select("[data-inline-latex]")
    ]
    matches = [m for f in formulas for m in re.findall(r"\\(sin|cos)x=", f)]
    images = soup.find_all("img")
    if not matches or len(images) != 1:
        raise UnsupportedCondition(
            "the parent must identify its trigonometric function and one circle"
        )
    image = images[0]
    part = image.find_parent("li")
    position = (
        "outside"
        if part is None
        else "after-intro"
        if any(str(n).strip() for n in image.previous_siblings)
        else "before-intro"
    )
    return (
        (S if matches[0] == "sin" else C),
        ("полный квадрат" in text),
        any(re.search(r"\(-\d+\)\^\{?k", f) for f in formulas),
        position,
    )


def select(series, bounds):
    lo, hi, lc, uc = bounds
    if hi - lo > 20 or max(abs(lo), abs(hi)) > 1000:
        raise UnsupportedCondition(
            "the reviewed interval must have bounded rational multiples of pi"
        )
    selected = set()
    trace = []
    for offset, period in series:
        start = int(sp.ceiling((lo - offset) / period))
        end = int(sp.floor((hi - offset) / period))
        if not lc and offset + start * period == lo:
            start += 1
        if not uc and offset + end * period == hi:
            end -= 1
        values = tuple(offset + k * period for k in range(start, end + 1))
        selected.update(values)
        trace.append((offset, period, start, end, values))
    return tuple(sorted(selected)), tuple(trace)


def analyze(formula, interval, bounds, parent_html):
    preferred, square, alternating, position = parent_style(parent_html)
    raw, identities = compile_equation(formula)
    reduced, branches = solve_branches(raw, preferred)
    residues = tuple(sorted({q for b in branches for q in b.residues}))
    if len(branches) == 1 and all(
        power[0] % 2 == 0
        for power in sp.Poly(branches[0].polynomial, branches[0].variable).monoms()
    ):
        series = periodic(residues)
    else:
        series = tuple(
            dict.fromkeys(
                s
                for b in branches
                for v in sorted(
                    b.values, key=cmp_to_key(compare), reverse=(b.variable == C)
                )
                for s in periodic(table(b.variable, v))
            )
        )
    qbounds = tuple(sp.cancel(b / sp.pi) for b in bounds[:2]) + bounds[2:]
    if any(q.is_Rational is not True for q in qbounds[:2]):
        raise UnsupportedCondition(
            "this circle family requires rational-pi interval endpoints"
        )
    selected, trace = select(series, qbounds)
    return Analysis(
        formula,
        raw,
        identities,
        reduced,
        branches,
        residues,
        series,
        selected,
        trace,
        interval,
        qbounds,
        preferred,
        square,
        alternating,
        position,
    )


def build_context_repair_plan(
    context, *, parent_solution_html="", generated_solution_assets=()
):
    from .exam_input import repair
    from .exam_trigonometric_circle import image, read
    from .exam_trigonometric_proof import render

    parts, formula, interval, bounds = read(context)
    a = analyze(formula, interval, bounds, parent_solution_html)
    markup, key, asset_changes = image(context, a, generated_solution_assets)
    plan = repair(parts, *render(a, markup))
    changes = list(plan.transformations)
    if not any(
        t["transformation_target_id"].startswith("section:solution") for t in changes
    ) and (parts[2] or {}).get("asset_keys") != [key]:
        from ..word_problems.common import rewrite

        changes.append(rewrite(parts[2], "solution", "Решение", plan.solution_html))
    for t in changes:
        if t["transformation_target_id"].startswith("section:solution"):
            t["value"]["asset_keys"] = [key]
    from dataclasses import replace

    return replace(plan, transformations=tuple(asset_changes) + tuple(changes))
