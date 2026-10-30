"""A first-blue draw tree with the remaining population shown at each node."""


def render_svg(red, blue, position):
    x = max(position * 65 + 15, (position - 1) * 65 + (red + blue - 1) * 8.5 + 30)
    width = max(450, x + (red + blue - 1) * 8.5 + 80)
    height = position * 130 + 55
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}"><g font-family="Times New Roman,serif" font-size="18">'
    ]
    for k in range(position):
        y = 35 + k * 130
        remaining_red = red - k
        total = remaining_red + blue
        left = x - 65
        right = x + 65
        for i in range(total):
            color = "#ff0000" if i < remaining_red else "#3366ff"
            cx = x + (i - (total - 1) / 2) * 17
            parts.append(f'<circle cx="{cx}" cy="{y - 20}" r="5" fill="{color}"/>')
        for cx, numerator, color in (
            (left, remaining_red, "#ff0000"),
            (right, blue, "#3366ff"),
        ):
            parts.append(
                f'<path d="M{x} {y}L{cx} {y + 90}" fill="none" stroke="{color}"/><circle cx="{cx}" cy="{y + 96}" r="5" fill="{color}"/>'
            )
            mx = (x + cx) / 2
            my = y + 42
            parts.append(
                f'<rect x="{mx - 13}" y="{my - 18}" width="26" height="39" fill="white"/><text x="{mx}" y="{my - 4}" text-anchor="middle">{numerator}</text><path d="M{mx - 10} {my}h20" stroke="black"/><text x="{mx}" y="{my + 18}" text-anchor="middle">{total}</text>'
            )
        if k == position - 1:
            parts.append(
                f'<rect x="{right - 13}" y="{y + 84}" width="26" height="24" fill="none" stroke="#1647b3"/>'
            )
        x = left
    parts.append("</g></svg>")
    return "".join(parts)
