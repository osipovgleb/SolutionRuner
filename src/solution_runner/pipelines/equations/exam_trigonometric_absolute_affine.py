"""Certify one affine absolute value and retain each original sign case."""

import re
from dataclasses import dataclass, replace

import sympy as sp
from bs4 import BeautifulSoup

from ..word_problems.common import UnsupportedCondition
from .exam_trigonometric_absolute import R, RootPlaceholderParser
from .exam_trigonometric_compile import C, S
from .exam_trigonometric_methods import Equation, ExamAngleParser
from .exam_trigonometric_radical_equation import compile_values
from .power_arithmetic import clean


@dataclass(frozen=True)
class AbsoluteAffine:
    inner: sp.Expr
    right: sp.Expr
    split_sign: bool
    phase: tuple | None
    intermediate_image: bool


def operands(formula):
    text = clean(formula).removesuffix(".")
    if text.count("|") != 2 or text.count("=") != 1:
        raise UnsupportedCondition("one complete affine absolute equality is required")
    plain = re.sub(r"\\[A-Za-z]+", "", text).replace("x", "")
    if re.search(r"[A-Za-z]", plain) or re.search(r"\\(?:alpha|beta|gamma)", text):
        raise UnsupportedCondition("the original absolute equality may contain only x")
    start, end = text.index("|"), text.rindex("|")
    atoms, denominators = {}, []
    inner = (
        ExamAngleParser(
            text[start + 1 : end].replace("x", r"\alpha"), atoms, denominators
        )
        .parse()
        .value
    )
    text = text[:start] + "(r)" + text[end + 1 :]
    values = [
        RootPlaceholderParser(part.replace("x", r"\alpha"), atoms, denominators)
        .parse()
        .value
        for part in text.split("=")
    ]
    if not atoms or any(a.variable != r"\alpha" for a in atoms.values()):
        raise UnsupportedCondition("the absolute equation must use the original x")
    (left, right, inner), poles, identities = compile_values(
        [*values, inner], atoms, denominators
    )
    difference = sp.expand(left - right)
    coefficient = difference.coeff(R)
    target = sp.cancel(-difference.subs(R, 0) / coefficient) if coefficient else sp.nan
    if (
        coefficient == 0
        or coefficient.free_symbols
        or coefficient.is_real is not True
        or sp.expand(difference - coefficient * (R - target)) != 0
    ):
        raise UnsupportedCondition(
            "one nonzero scalar absolute coefficient is required"
        )
    if poles or any(
        not v.is_polynomial(S, C) or sp.Poly(v, S, C).total_degree() > 1
        for v in (inner, target)
    ):
        raise UnsupportedCondition(
            "denominator-free affine sine/cosine expressions are required"
        )
    if sp.expand(inner**2 - target**2) == 0:
        raise UnsupportedCondition("an absolute identity may have intervals of roots")
    return inner, target, identities


def parent_method(html, inner, right):
    from .exam_trigonometric_shifted import candidates, formula

    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ").replace("\xad", "").lower().replace("ё", "е")
    if any(v in text for v in ("другое решение", "еще одно решение")):
        raise UnsupportedCondition("additional absolute methods need review")
    forms = [clean(n["data-inline-latex"]) for n in soup.select("[data-inline-latex]")]
    source_pairs = []
    for f in forms:
        for part in re.split(r"\\(?:iff|Leftrightarrow)", f):
            if part.count("|") != 2:
                continue
            try:
                u, v, _ = operands(part)
            except UnsupportedCondition:
                continue
            source_pairs.append((u, v))
    if not source_pairs:
        raise UnsupportedCondition(
            "the parent must retain the complete affine absolute equation"
        )
    name = {S: r"\sinx", C: r"\cosx"}.get(inner)
    split = bool(name and name + r"\ge0" in forms and name + r"\lt0" in forms)
    if split and not any(u == inner for u, _ in source_pairs):
        raise UnsupportedCondition(
            "the parent sign split must use the same absolute function"
        )
    if not split:
        variable = next(
            (v for v in (S, C) if sp.cancel(right / v).is_negative is True), None
        )
        token = {S: r"\sinx\le0", C: r"\cosx\le0"}.get(variable)
        if (
            token is None
            or not any(token in f for f in forms)
            or not any(
                sp.cancel(v / variable).is_negative is True for _, v in source_pairs
            )
        ):
            raise UnsupportedCondition(
                "the parent's complete absolute sign restriction needs review"
            )
    phases = tuple(
        dict.fromkeys((n, q) for f in forms for n, _, q in candidates(formula(f)))
    )
    if len(phases) > 1:
        raise UnsupportedCondition(
            "one reviewed inverse-phase absolute branch is required"
        )
    images = soup.find_all("img")
    intermediate = False
    if split and images:
        if len(images) != 1:
            raise UnsupportedCondition("one original absolute-case figure is required")
        before = [
            clean(n["data-inline-latex"])
            for n in images[0].find_all_previous(attrs={"data-inline-latex": True})
        ]
        intermediate = bool(before and before[0] == name + r"\lt0")
        if not intermediate:
            raise UnsupportedCondition("the absolute-case figure stage needs review")
    return split, phases[0] if phases else None, intermediate


def compile_absolute(formula, parent_html):
    text = clean(formula)
    from .exam_trigonometric_radical_equation import variable_radicals

    if text.count("|") != 2 or variable_radicals(text):
        return None
    inner, right, identities = operands(text)
    split, phase, intermediate = parent_method(parent_html, inner, right)
    return Equation(
        sp.expand(inner**2 - right**2),
        identities,
        sp.S.One,
        absolute_affine=AbsoluteAffine(inner, right, split, phase, intermediate),
    )


def phase_branch(branch, phase):
    from .exam_trigonometric_radical_equation import trig_polynomial

    if phase is None:
        return branch
    name, shift = phase
    raw = branch.original if branch.original is not None else branch.polynomial
    basis = trig_polynomial(name, sp.S.One, shift)
    weight = sp.cancel(raw / basis)
    if weight.free_symbols or weight == 0:
        return branch
    variable = S if name == "sin" else C
    return replace(
        branch,
        variable=variable,
        polynomial=variable,
        candidates=(sp.S.Zero,),
        values=(sp.S.Zero,),
        original=raw if weight > 0 else -raw,
        angle_shift=shift,
    )


def cases(data, allow_inverse=False):
    from .exam_trigonometric import solve_branches
    from .exam_trigonometric_domain import restrict

    result = []
    for negative in (False, True):
        raw = sp.expand(data.inner + (data.right if negative else -data.right))
        if raw == 0:
            raise UnsupportedCondition(
                "an absolute branch with an interval of roots needs review"
            )
        _, formal = solve_branches(raw, S, allow_inverse)
        formal = tuple(phase_branch(b, data.phase) for b in formal)
        condition = (
            (-data.inner if negative else data.inner) if data.split_sign else data.right
        )
        strict = data.split_sign and negative
        accepted = restrict(formal, condition, strict=strict)
        result.append((condition, strict, raw, formal, accepted))
    if data.intermediate_image and not any(b.angle_shift for b in result[1][3]):
        raise UnsupportedCondition(
            "the original intermediate image must precede its inverse-phase branch"
        )
    if data.phase is not None and not any(
        b.angle_shift for _, _, _, formal, _ in result for b in formal
    ):
        raise UnsupportedCondition(
            "the parent inverse-phase method must match a computed absolute branch"
        )
    return tuple(result)
