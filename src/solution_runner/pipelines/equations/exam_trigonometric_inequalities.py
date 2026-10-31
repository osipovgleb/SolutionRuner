"""Select the members of each certified root family with its own parameter."""

import sympy as sp

from ..probability.common import line
from ..word_problems.water_season_proof import inline


def inequality_selection(a):
    from .exam_trigonometric_proof import pi

    def display(value):
        return sp.latex(
            sp.expand(
                value.xreplace(
                    {
                        arc: sp.pi / 2 - sp.asin(arc.args[0])
                        for arc in value.atoms(sp.acos)
                    }
                )
            )
            if a.sine_inverse
            else value,
            inv_trig_style="full",
        )

    html = (
        "<p>Найдём корни на промежутке "
        + inline(a.interval)
        + ". Решим неравенства для целого параметра каждой серии:</p>"
    )
    inverse = (
        set().union(*(q.atoms(sp.acos) for q in a.residues)) if a.residues else set()
    )
    for angle in inverse:
        if a.sine_inverse:
            html += "<p>Для главного значения арксинуса положительного числа используем его область значений:</p>"
            html += line(
                "0<"
                + sp.latex(sp.asin(angle.args[0]), inv_trig_style="full")
                + r"<\frac{\pi}{2}"
            )
        else:
            html += "<p>Для главного значения арккосинуса используем его область значений:</p>"
            html += line("0<" + sp.latex(angle, inv_trig_style="full") + r"<\pi")
    lo, hi, lc, uc = a.bounds
    from .exam_trigonometric_restricted_families import selection_rows

    for offset, period, start, end, values, name, indices in selection_rows(a):
        parameter = sp.Symbol(name, integer=True)
        html += line(
            pi(lo)
            + (r"\le" if lc else "<")
            + display(sp.expand(offset * sp.pi + period * sp.pi * parameter))
            + (r"\le" if uc else "<")
            + pi(hi)
        )
        lower, upper, left_closed, right_closed = (
            (lo, hi, lc, uc) if period > 0 else (hi, lo, uc, lc)
        )
        html += line(
            display(sp.simplify((lower - offset) / period))
            + (r"\le" if left_closed else "<")
            + " "
            + name
            + " "
            + (r"\le" if right_closed else "<")
            + display(sp.simplify((upper - offset) / period))
        )
        if not indices:
            html += "<p>Подходящих целых значений " + name + " нет.</p>"
        else:
            html += line(name + r"\in\{" + ";".join(str(k) for k in indices) + r"\}")
            for root in values:
                html += line("x=" + pi(root, sine_inverse=a.sine_inverse))
    return html
