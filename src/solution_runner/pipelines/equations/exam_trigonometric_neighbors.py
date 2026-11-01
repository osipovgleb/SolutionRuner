"""Select a finite block of progression members using certified neighboring bounds."""

from bs4 import BeautifulSoup

from ..probability.common import line
from ..word_problems.common import UnsupportedCondition
from ..word_problems.water_season_proof import inline
from .exam_scalar import compare


def reviewed(html):
    soup = BeautifulSoup(html, "html.parser")
    if soup.find("img"):
        return False
    text = " ".join(soup.get_text(" ").replace("\xad", "").lower().split())
    formulas = "".join(
        "".join(n["data-inline-latex"].split())
        for n in soup.select("[data-inline-latex]")
    )
    return (
        ("рассмотрим" in text and "оценим эти корни" in text and "k" in formulas)
        or (
            "левее отрезка" in text
            and "правее отрезка" in text
            and all(token in formulas for token in (r"k\le", "k=", r"k\ge"))
        )
        or (
            "при таких" in text
            and "решений на отрезке" in text
            and all(token in formulas for token in (r"k\le", "k=", r"k\ge"))
        )
        or (
            "члены обеих серий" in text
            and "больше" in text
            and "меньше" in text
            and "других решений" in text
            and all(token in formulas for token in (r"k\le", "k=", r"k\ge"))
        )
    )


def certify(series, bounds):
    from .exam_trigonometric import select

    selected, rows = select(series, bounds)
    lo, hi, lc, uc = bounds
    for q, period, start, end, roots in rows:
        if compare(q + (start - 1) * period, lo) >= (0 if lc else 1) or compare(
            q + (end + 1) * period, hi
        ) <= (0 if uc else -1):
            raise UnsupportedCondition(
                "the neighboring progression members must lie outside the interval"
            )
        if any(
            compare(root, lo) < (0 if lc else 1)
            or compare(root, hi) > (0 if uc else -1)
            for root in roots
        ):
            raise UnsupportedCondition(
                "every selected progression member must satisfy both original bounds"
            )
    return selected, rows


def proof(a):
    from .exam_trigonometric_proof import pi, series_lines

    html = (
        "<p>Отберём корни на промежутке "
        + inline(a.interval)
        + ". Рассмотрим подходящие целые индексы и соседние члены каждой возрастающей прогрессии.</p>"
    )
    html += (
        "<p>При сравнении с числовыми границами учитываем строгие оценки числа π:</p>"
        + line(r"3<\pi<\frac{22}{7}")
    )
    for q, period, start, end, roots in a.selections:
        html += line(series_lines(((q, period),))[0] + r",\quad k\in\mathbb Z")
        html += "<p>Все меньшие индексы не дают корней внутри промежутка:</p>"
        html += line(
            "k"
            + r"\le "
            + str(start - 1)
            + r"\quad\Longrightarrow\quad x\le "
            + pi(q + (start - 1) * period)
            + ("<" if compare(q + (start - 1) * period, a.bounds[0]) < 0 else r"\le ")
            + pi(a.bounds[0])
        )
        for k, root in zip(range(start, end + 1), roots):
            html += line("k=" + str(k) + r"\quad\Longrightarrow\quad x=" + pi(root))
            html += line(
                pi(a.bounds[0])
                + (r"\le " if a.bounds[2] else "<")
                + pi(root)
                + (r"\le " if a.bounds[3] else "<")
                + pi(a.bounds[1])
            )
        html += "<p>Все большие индексы не дают корней внутри промежутка:</p>"
        html += line(
            "k"
            + r"\ge "
            + str(end + 1)
            + r"\quad\Longrightarrow\quad x\ge "
            + pi(q + (end + 1) * period)
            + (">" if compare(q + (end + 1) * period, a.bounds[1]) > 0 else r"\ge ")
            + pi(a.bounds[1])
        )
    return html
