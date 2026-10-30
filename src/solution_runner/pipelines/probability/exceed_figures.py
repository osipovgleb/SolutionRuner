"""Trees and outcome tables for a die crossing a positive sum boundary."""

from fractions import Fraction
from html import escape
from itertools import product

TREE_REUSE = {
    (3, 2): "d7f3ea83-1190-44d2-9c00-3e94420a85cb",
    (3, 3): "d6ec56b8-0bd5-4388-9319-5cbde5711011",
    (2, 2): "3525c749-2a8c-47ff-bae1-e0b478d76eef",
    (2, 3): "71424338-04d4-4ab2-9a3c-0b641673635c",
}
TABLE_REUSE = {
    (3, 2): "f679cedf-88ef-4915-9a36-6ca1e509dcf6",
    (2, 2): "07fd26da-75aa-4b99-bd1d-dadfe026f1e3",
}
TREE_KEY = "generated_first_exceed_tree"
TABLE_KEY = "generated_first_exceed_table"
TREE_ALT = "Дерево первого превышения суммы на указанном броске"
TABLE_ALT = "Таблица исходов первого превышения суммы"


def eligible_prefixes(threshold, throws):
    return tuple(
        row for row in product(range(1, 7), repeat=throws - 1) if sum(row) <= threshold
    )


def render_table(threshold, throws):
    rows = (
        tuple(product(range(1, 7), repeat=throws - 1))
        if throws <= 2
        else eligible_prefixes(threshold, throws)
    )
    width = 440
    cell = 43
    top = 85
    height = top + cell * (len(rows) + 1) + 45
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}"><g font-family="Times New Roman,serif" font-size="20">'
    ]
    parts.append(f'<text x="260" y="28" text-anchor="middle">Бросок {throws}</text>')
    parts.append(
        '<text x="76" y="68" text-anchor="middle" font-size="13">Первые броски</text>'
    )
    for j in range(6):
        parts.append(
            f'<text x="{135 + cell * (j + 0.5)}" y="68" text-anchor="middle">{j + 1}</text>'
        )
    for i, row in enumerate(rows):
        y = top + i * cell
        label = ",".join(map(str, row)) or "—"
        parts.append(
            f'<text x="76" y="{y + cell / 2 + 7}" text-anchor="middle">{escape(label)}</text>'
        )
        for j in range(6):
            x = 135 + j * cell
            parts.append(
                f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" fill="white" stroke="black"/>'
            )
            if sum(row) <= threshold < sum(row) + j + 1:
                parts.append(
                    f'<path data-prefix="{label}" data-face="{j + 1}" d="M{x + 10} {y + cell / 2}h{cell - 20} M{x + cell / 2} {y + 10}v{cell - 20}" stroke="#099c4a" stroke-width="3"/>'
                )
    if throws > 2:
        parts.append(
            f'<text x="220" y="{height - 22}" text-anchor="middle" font-size="14">Другие первые броски завершили игру раньше.</text>'
        )
    parts.append("</g></svg>")
    return "".join(parts)


def render_tree(threshold, throws):
    def options(s, depth):
        if depth == throws - 1:
            return [
                (tuple(range(1, min(6, threshold - s) + 1)), False),
                (tuple(range(max(1, threshold - s + 1), 7)), True),
            ]
        bound = min(6, threshold - s - (throws - depth - 2))
        return [((face,), None) for face in range(1, bound + 1)] + [
            (tuple(range(max(1, bound + 1), 7)), False)
        ]

    def leaves(s, depth):
        return sum(
            leaves(s + faces[0], depth + 1) if status is None else 1
            for faces, status in options(s, depth)
            if faces
        )

    width = max(700, 180 + 100 * leaves(0, 0))
    height = 80 + 110 * throws
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}"><g font-family="Times New Roman,serif" font-size="18">'
    ]

    def branch(s, depth, x, left, right, weight):
        cursor = left
        unit = (right - left) / leaves(s, depth)
        for faces, status in options(s, depth):
            if not faces:
                continue
            span = unit * (leaves(s + faces[0], depth + 1) if status is None else 1)
            cx = cursor + span / 2
            cy = 40 + (depth + 1) * 110
            color = "#ff2222" if status is False else "#099c4a"
            parts.append(
                f'<path d="M{x} {40 + depth * 110}L{cx} {cy - 15}" stroke="{color}" fill="none" stroke-width="1.5"/>'
            )
            mx = (x + cx) / 2
            my = (40 + depth * 110 + cy) / 2
            probability = Fraction(len(faces), 6)
            parts.append(
                f'<rect x="{mx - 12}" y="{my - 18}" width="24" height="34" fill="white"/>'
            )
            if probability == 1:
                parts.append(
                    f'<text x="{mx}" y="{my + 5}" text-anchor="middle">1</text>'
                )
            else:
                parts.append(
                    f'<text x="{mx}" y="{my - 4}" text-anchor="middle">{len(faces)}</text><path d="M{mx - 8} {my}h16" stroke="black"/><text x="{mx}" y="{my + 16}" text-anchor="middle">6</text>'
                )
            label = ",".join(map(str, faces))
            if len(label) > 7:
                label = f"{faces[0]},…,{faces[-1]}"
            attr = (
                f' data-success-probability="{weight * probability}"'
                if status is True
                else ""
            )
            parts.append(
                f'<text x="{cx}" y="{cy + 5}" text-anchor="middle" fill="{color}"{attr}>{label}</text>'
            )
            if status is None:
                branch(
                    s + faces[0],
                    depth + 1,
                    cx,
                    cursor,
                    cursor + span,
                    weight * probability,
                )
            cursor += span

    branch(0, 0, width / 2, 150, width - 25, Fraction(1))
    for depth in range(throws):
        parts.append(f'<text x="8" y="{155 + depth * 110}">Бросок {depth + 1}</text>')
    parts.append("</g></svg>")
    return "".join(parts)
