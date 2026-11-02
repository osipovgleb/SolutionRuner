"""Keep the parent's sign split or global nonnegative-right-side system."""

from ..probability.common import line
from .exam_trigonometric_absolute_affine import cases
from .exam_trigonometric_compile import C, S


def retained_lines(branches, *, center=False):
    from .exam_trigonometric import periodic
    from .exam_trigonometric_inverse import centred
    from .exam_trigonometric_proof import series_lines

    roots = periodic(q for branch in branches for q in branch.residues)
    if center:
        roots = centred(roots)
    return (
        "".join(line(f + r",\quad k\in\mathbb Z") for f in series_lines(roots))
        if roots
        else "<p>В этом случае корней нет.</p>"
    )


def common_steps(a, factor_text):
    import sympy as sp

    from .exam_scalar import compare
    from .exam_trigonometric import solve_branches
    from .exam_trigonometric_domain import restrict
    from .exam_trigonometric_proof import formula, polynomial
    from .power_arithmetic import clean

    data = a.absolute_affine
    factor = -data.right
    quotient = sp.cancel(data.inner / factor)
    original = clean(a.original)
    inner = original[original.index("|") + 1 : original.rindex("|")]
    html = "<p>Преобразуем выражение под модулем и сохраним общий множитель:</p>"
    html += line(inner + "=" + factor_text + "(" + formula(quotient) + ")")
    html += "<p>В каждом из двух линейных равенств вынесем общий множитель:</p>"
    for sign in (1, -1):
        html += line(factor_text + "(" + formula(quotient + sign) + ")=0")
    html += "<p>Произведение равно нулю, если хотя бы один множитель равен нулю. На общий множитель не делим: он тоже даёт корни.</p>"
    html += line(factor_text + "=0")
    _, zero = solve_branches(factor, S, a.allow_inverse)
    html += retained_lines(zero)
    for level in (-1, 1):
        html += line(formula(quotient) + "=" + str(level))
        raw = sp.expand(quotient - level)
        if not raw.free_symbols:
            html += "<p>Ненулевой постоянный множитель корней не даёт.</p>"
            continue
        _, formal = solve_branches(raw, S, a.allow_inverse)
        for branch in formal:
            html += polynomial(branch, allow_inverse=a.allow_inverse)
        accepted = restrict(formal, data.right)
        html += "<p>Проверим исходное ограничение на знак общего множителя:</p>"
        values = {
            sp.simplify(factor.subs({S: sp.sin(q * sp.pi), C: sp.cos(q * sp.pi)}))
            for branch in formal
            for q in branch.residues
        }
        for value in sorted(values, key=sp.default_sort_key):
            html += line(
                formula(factor)
                + "="
                + sp.latex(value)
                + (r"\le0" if compare(value, sp.S.Zero) <= 0 else ">0")
            )
        html += retained_lines(accepted)
    return html


def proof(a, image=""):
    import sympy as sp

    from .exam_trigonometric_proof import families, formula, polynomial
    from .power_arithmetic import clean

    data = a.absolute_affine
    u, v = formula(data.inner), formula(data.right)
    factor_text = ""
    if data.common is not None:
        name, weight = data.common
        factor_text = (sp.latex(weight) + r"\cdot " if weight != 1 else "") + name
        original = clean(a.original)
        u = original[original.index("|") + 1 : original.rindex("|")]
        v = "-(" + factor_text + ")"
    html = line(a.original)
    for text, value in a.identities:
        if data.common is None and value not in (S, C):
            html += line(text + "=" + formula(value))
    if data.common is None:
        html += line(r"\left|" + u + r"\right|=" + v)
    if not data.split_sign:
        html += "<p>Модуль неотрицателен. Равенство равносильно системе: правая часть неотрицательна, а выражение под модулем совпадает с ней или противоположно ей:</p>"
        html += line(v + r"\ge0")
    if data.common is not None:
        html += line(factor_text + r"\le0")
        html += common_steps(a, factor_text)
    else:
        for index, (_, _, raw, formal, accepted) in enumerate(
            cases(data, a.allow_inverse)
        ):
            if data.split_sign:
                html += "<p>Рассмотрим случай:</p>" + line(
                    u + ("<0" if index else r"\ge0")
                )
                if index:
                    html += image
                html += line(("-(" + u + ")" if index else u) + "=" + v)
            else:
                html += line(u + "=" + ("-(" + v + ")" if index else v))
            html += line(formula(raw) + "=0")
            for branch in formal:
                html += polynomial(branch, allow_inverse=a.allow_inverse)
            html += "<p>Проверим знак в рассматриваемом случае и оставим только подходящие серии:</p>"
            html += retained_lines(accepted, center=data.split_sign)
    html += "<p>Объединим решения обоих случаев:</p>"
    html += (
        "".join(line(f + r",\quad k\in\mathbb Z") for f in families(a))
        if a.series
        else "<p>Корней нет.</p>"
    )
    return "<p>Раскроем модуль с сохранением условий на знак:</p>", html
