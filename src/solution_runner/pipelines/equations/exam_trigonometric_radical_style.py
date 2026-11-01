"""Read the complete reviewed radical methods and their original note placement."""

from bs4 import BeautifulSoup

from ..word_problems.common import UnsupportedCondition
from .power_arithmetic import balanced


def normalized(node):
    return " ".join(
        node.get_text(" ").replace("\xad", "").lower().replace("ё", "е").split()
    )


def variable_roots(formulas):
    result = []
    start = 0
    while (index := formulas.find(r"\sqrt{", start)) >= 0:
        inside, start = balanced(formulas, index + 5)
        if "x" in inside:
            result.append(inside)
    return result


def kind(html):
    soup = BeautifulSoup(html, "html.parser")
    text = normalized(soup)
    formulas = " ".join(
        "".join(n["data-inline-latex"].split())
        for n in soup.select("[data-inline-latex]")
    )
    if "косинуса тройного угла" in text and "косинуса половинного угла" in text:
        return "half_tangent"
    if (
        "синус и косинус имеют один знак" in text
        and "положительны" in text
        and r"\ctg" in formulas
        and r"\tg" in formulas
    ):
        return "amgm"
    if (
        "каждое из слагаемых" in text
        and "нечетных" in text
        and "не меньше" in text
        and r"\cos2x=-1" in formulas
    ):
        return "extremal"
    return ""


def split(html, formula):
    from .exam_trigonometric_radical_equation import variable_radicals

    if not variable_radicals(formula):
        return html, ()
    soup = BeautifulSoup(html, "html.parser")
    method = kind(html)
    if not method:
        return html, ()
    paragraphs = soup.find_all("p")
    markers = [
        p
        for p in paragraphs
        if normalized(p).startswith(
            ("приведем идею другого решения", "приведем другое решение уравнения")
        )
    ]
    if not markers:
        return html, ()
    if len(markers) != 1 or soup.find("img"):
        raise UnsupportedCondition(
            "one complete reviewed radical-note block without figures is required"
        )
    marker = markers[0]
    following = list(marker.next_siblings)
    if method == "half_tangent" and marker.parent.name == "section":
        tail = [n for n in marker.parent.next_siblings if str(n).strip()]
        if tail and (
            len(tail) != 1
            or getattr(tail[0], "name", None) != "section"
            or tail[0].get("data-solution-title", "").lower().rstrip(".")
            != "альтернативное решение"
        ):
            raise UnsupportedCondition(
                "exactly one reviewed final alternative section is required"
            )
        following += tail
    notes = BeautifulSoup("".join(map(str, following)), "html.parser")
    text = normalized(notes)
    if any(s in text for s in ("приведем", "еще одно решение", "другое решение")):
        raise UnsupportedCondition("unknown additional radical method")
    if method == "half_tangent":
        if not all(
            s in text
            for s in ("перенесем", "неположительна", "неотрицательна", "посторонний")
        ):
            raise UnsupportedCondition(
                "both the rational-cosine and opposite-sign-square notes are required"
            )
        placement = False
    elif method == "amgm":
        if (
            not all(s in text for s in ("разделим", "внесем", "положительны"))
            or marker.find_parent("li") is None
            or marker.find_parent("li").get("data-list-marker") != "б)"
        ):
            raise UnsupportedCondition(
                "the positive-tangent alternative must follow selection in part b"
            )
        placement = True
    else:
        raise UnsupportedCondition(
            "this radical method has no reviewed alternative block"
        )
    for node in following:
        node.extract()
    marker.extract()
    return str(soup), (placement, method)
