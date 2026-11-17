"""Explain reviewed circle labels and selection of trigonometric roots."""

import sympy as sp

from ..word_problems.common import UnsupportedCondition


def angle_caption(entry, a):
    from ..probability.common import line
    from ..word_problems.water_season_proof import inline
    from .exam_trigonometric_proof import pi

    multiplier = sp.Rational(entry.get("circle_scale", "1"))
    if multiplier == 1:
        return ""
    angle = sp.latex(multiplier * sp.Symbol("x", real=True))
    lo, hi, lc, uc = a.bounds
    html = (
        "<p>На окружности рассматриваем угол "
        + inline(angle)
        + ". Пересчитаем границы промежутка и выбранные корни:</p>"
    )
    html += line(
        pi(lo * multiplier)
        + (r"\le" if lc else "<")
        + angle
        + (r"\le" if uc else "<")
        + pi(hi * multiplier)
    )
    for q in a.selected:
        html += line(
            angle
            + "="
            + pi(q * multiplier)
            + r"\quad\Longleftrightarrow\quad x="
            + pi(q)
        )
    return html


def series_caption(entry, a):
    from ..probability.common import line
    from .exam_trigonometric import C
    from .exam_trigonometric_inverse import level_series
    from .exam_trigonometric_proof import series_lines

    marks = entry.get("series_marks")
    if not marks:
        return ""
    if (
        a.scale != sp.Rational(entry["series_angle"])
        or len(a.branches) != 1
        or a.branches[0].variable != C
        or {sp.Rational(m["value"]) for m in marks} != set(a.branches[0].values)
    ):
        raise UnsupportedCondition("the marked series must match all cosine levels")
    html = "<p>На рисунке обозначены серии:</p>"
    for mark in marks:
        if mark["label"] not in ("*", "**"):
            raise UnsupportedCondition("unknown source series label")
        series = tuple(
            (q / a.scale, p / a.scale)
            for q, p in level_series(C, sp.Rational(mark["value"]))
        )
        if any(s not in a.series for s in series):
            raise UnsupportedCondition("the circle series marker changed")
        html += "".join(
            line(text + r",\quad k\in\mathbb Z\quad(" + mark["label"] + ")")
            for text in series_lines(series)
        )
    return html


def point_caption(entry, a):
    from ..word_problems.water_season_proof import inline
    from .exam_trigonometric import S
    from .exam_trigonometric_inverse import decode, ordered
    from .exam_trigonometric_proof import formula

    letters = entry.get("point_letters")
    if not letters:
        return ""
    if (
        len(a.branches) != 1
        or ordered(decode(q) for q in letters.values()) != a.residues
    ):
        raise UnsupportedCondition(
            "the lettered circle must describe all computed roots"
        )
    variable = a.branches[0].variable
    function = sp.sin if variable == S else sp.cos
    groups = {}
    for letter, q in letters.items():
        value = sp.simplify(function(decode(q) * sp.pi))
        groups.setdefault(value, []).append(letter)
    return "".join(
        "<p>Корни уравнения "
        + inline(formula(variable) + "=" + sp.latex(value))
        + "изображаются точками "
        + " и ".join(names)
        + ".</p>"
        for value, names in groups.items()
    )


def selection_proof(a, image, *, paired=False):
    from ..probability.common import line
    from ..word_problems.water_season_proof import inline
    from .exam_trigonometric_proof import pi

    quadratic = a.affine is not None and a.affine.quadratic
    lead = (
        "С помощью числовой окружности отберём периодические корни"
        if quadratic
        else "С помощью числовой окружности отберём корни"
    )
    second = (
        "<p>"
        + lead
        + ", принадлежащие промежутку "
        + inline(a.interval)
        + ". Границы дуги учитываем в соответствии с квадратными и круглыми скобками:</p>"
    )
    if paired and a.radical_product is not None:
        second = image + second
    roots = a.selected
    if quadratic:
        from .exam_trigonometric import select
        from .exam_trigonometric_affine_proof import isolated_selection

        second = isolated_selection(a) + second
        roots = select(a.series, a.bounds)[0]
    lo, hi, lc, uc = a.bounds
    if a.image_position == "selection" or (
        a.log_product is not None
        and paired
        and a.log_product.selection_image_position == "selection"
    ):
        second += image
    for root in roots:
        second += line(
            pi(lo, sine_inverse=a.sine_inverse)
            + (r"\le" if lc else "<")
            + pi(root, sine_inverse=a.sine_inverse)
            + (r"\le" if uc else "<")
            + pi(hi, sine_inverse=a.sine_inverse)
        )
    if not roots:
        second += (
            "<p>Периодических корней на указанной дуге нет.</p>"
            if quadratic
            else "<p>На указанной дуге точек решения нет.</p>"
        )
    return second
