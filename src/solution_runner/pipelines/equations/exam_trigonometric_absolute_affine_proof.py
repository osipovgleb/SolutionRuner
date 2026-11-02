"""Keep the parent's sign split or global nonnegative-right-side system."""

from ..probability.common import line
from .exam_trigonometric_absolute_affine import cases
from .exam_trigonometric_compile import C, S


def proof(a, image=""):
    from .exam_trigonometric import periodic
    from .exam_trigonometric_inverse import centred
    from .exam_trigonometric_proof import families, formula, polynomial, series_lines

    data = a.absolute_affine
    u, v = formula(data.inner), formula(data.right)
    html = line(a.original)
    for text, value in a.identities:
        if value not in (S, C):
            html += line(text + "=" + formula(value))
    html += line(r"\left|" + u + r"\right|=" + v)
    if not data.split_sign:
        html += "<p>Модуль неотрицателен. Равенство равносильно системе: правая часть неотрицательна, а выражение под модулем совпадает с ней или противоположно ей:</p>"
        html += line(v + r"\ge0")
    for index, (_, _, raw, formal, accepted) in enumerate(cases(data, a.allow_inverse)):
        if data.split_sign:
            html += "<p>Рассмотрим случай:</p>" + line(u + ("<0" if index else r"\ge0"))
            if index:
                html += image
            html += line(("-(" + u + ")" if index else u) + "=" + v)
        else:
            html += line(u + "=" + ("-(" + v + ")" if index else v))
        html += line(formula(raw) + "=0")
        for branch in formal:
            html += polynomial(branch, allow_inverse=a.allow_inverse)
        roots = periodic(q for branch in accepted for q in branch.residues)
        if data.split_sign:
            roots = centred(roots)
        html += "<p>Проверим знак в рассматриваемом случае и оставим только подходящие серии:</p>"
        html += (
            "".join(line(f + r",\quad k\in\mathbb Z") for f in series_lines(roots))
            if roots
            else "<p>В этом случае корней нет.</p>"
        )
    html += "<p>Объединим решения обоих случаев:</p>"
    html += (
        "".join(line(f + r",\quad k\in\mathbb Z") for f in families(a))
        if a.series
        else "<p>Корней нет.</p>"
    )
    return "<p>Раскроем модуль с сохранением условий на знак:</p>", html
