"""Compare global-extremum candidates using monotonicity and stated values."""

from fractions import Fraction
from itertools import pairwise

from ..probability.common import UnsupportedCondition, line
from .common import answer
from .graph_monotonic_chart import compare


def extremum(question, bands):
    span = question.span
    maximum = question.target == "наибольшее"
    sign = -1 if maximum else 1
    if (not span.lower_closed and bands[0][4] != -sign) or (
        not span.upper_closed and bands[-1][4] != sign
    ):
        raise UnsupportedCondition("an open endpoint may prevent a global extremum")
    nodes = {span.lower, span.upper}
    candidates = set()
    if span.lower_closed:
        candidates.add(span.lower)
    if span.upper_closed:
        candidates.add(span.upper)
    for first, second in pairwise(bands):
        point = first[1]
        if "x" not in point:
            raise UnsupportedCondition(
                "global comparisons need exact critical abscissae"
            )
        x = Fraction(point["x"])
        nodes.add(x)
        if first[4] == -sign and second[4] == sign:
            candidates.add(x)
    anchors = {x for a, _, b in question.comparisons for x in [a, b]}
    if (span.lower in anchors and not span.lower_closed) or (
        span.upper in anchors and not span.upper_closed
    ):
        raise UnsupportedCondition(
            "a comparison value is undefined at an open endpoint"
        )
    nodes.update(anchors)
    nodes = sorted(nodes)
    if nodes[0] != span.lower or nodes[-1] != span.upper:
        raise UnsupportedCondition(
            "a value comparison lies outside the function domain"
        )
    edges = []
    for a, b in pairwise(nodes):
        matching = [
            band
            for band in bands
            if Fraction(band[0]["x"]) <= a < b <= Fraction(band[1]["x"])
        ]
        if len(matching) != 1:
            raise UnsupportedCondition(
                "every comparison arc needs a monotonicity proof"
            )
        edges.append((a, b, True) if matching[0][4] > 0 else (b, a, True))
    for a, op, b in question.comparisons:
        if op == "=":
            edges.extend([(a, b, False), (b, a, False)])
        elif op in [">", r"\geq"]:
            edges.append((b, a, op == ">"))
        else:
            edges.append((a, b, op == "<"))
    winner = unique_winner(nodes, candidates, edges, maximum)
    html = (
        "<p>Сравним значения функции в соседних точках по направлению её изменения:</p>"
    )
    for a, b, strict in edges:
        html += line(
            "f("
            + answer(a)
            + ")"
            + ("<" if strict else r"\leq")
            + "f("
            + answer(b)
            + ")"
        )
    return winner, html


def minimum_value(question, bands, entry):
    span = question.span
    if span.lower <= question.domain.lower or span.upper >= question.domain.upper:
        raise UnsupportedCondition(
            "the value query must lie inside the function domain"
        )
    candidates = {span.lower, span.upper}
    for left, right in pairwise(bands):
        if left[4] < 0 < right[4]:
            p = left[1]
            if compare(p, span.lower) > 0 and compare(p, span.upper) < 0:
                if "x" not in p:
                    raise UnsupportedCondition(
                        "the minimum ordinate needs an exact abscissa"
                    )
                candidates.add(Fraction(p["x"]))
    points = {Fraction(p["x"]): p for p in entry["ordinate_points"]}
    if not candidates <= points.keys():
        raise UnsupportedCondition(
            "all endpoint and minimum ordinates must be reviewed"
        )
    exact = [(Fraction(points[x]["y"]), x) for x in candidates if "y" in points[x]]
    if not exact:
        raise UnsupportedCondition("an exact minimum ordinate is required")
    value, x = min(exact)
    if any(
        (
            Fraction(points[p]["y"])
            if "y" in points[p]
            else Fraction(points[p]["y_bounds"][0])
        )
        < value
        for p in candidates
    ):
        raise UnsupportedCondition("the graph does not prove the minimum ordinate")
    html = "<p>На отрезке сравниваем значения функции на концах и во внутренних точках минимума. Считываем с графика ординаты:</p>"
    for p in sorted(candidates):
        node = points[p]
        if "y" in node:
            html += line("f(" + answer(p) + ")=" + answer(node["y"]))
        else:
            low, high = node["y_bounds"]
            html += line(
                answer(low) + r"\leq f(" + answer(p) + r")\leq " + answer(high)
            )
    html += "<p>Самая низкая точка графика на данном отрезке имеет ординату:</p>"
    html += line("f(" + answer(x) + ")=" + answer(value))
    return answer(value), html


def unique_winner(nodes, candidates, edges, maximum):
    reach = {}
    for a, b, strict in edges:
        reach[a, b] = reach.get((a, b), False) or strict
    for k in nodes:
        for a in nodes:
            for b in nodes:
                if (a, k) in reach and (k, b) in reach:
                    reach[a, b] = reach.get((a, b), False) or reach[a, k] or reach[k, b]
    if any(reach.get((a, a)) for a in nodes):
        raise UnsupportedCondition("the supplied values contradict the sign chart")
    winners = [
        a
        for a in candidates
        if all(
            a == b or reach.get((b, a) if maximum else (a, b), False)
            for b in candidates
        )
    ]
    if len(winners) != 1:
        raise UnsupportedCondition(
            "the value comparisons do not prove a unique global extremum"
        )
    return winners[0]
