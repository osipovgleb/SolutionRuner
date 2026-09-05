import re
import colorsys
from pathlib import Path
from bs4 import BeautifulSoup, Comment


def _find_svg_tag(soup):
    for tag in soup.find_all(True):
        name = tag.name
        if not isinstance(name, str):
            continue
        if name.lower() == "svg" or name.lower().endswith(":svg"):
            return tag
    return None


def is_svg(soup):
    return _find_svg_tag(soup) is not None


def _parse_svg_soup(svg_source):
    try:
        soup = BeautifulSoup(svg_source, "xml")
        if _find_svg_tag(soup) is not None:
            return soup, None
    except Exception as exc:
        soup = None
        last_error = exc
    else:
        last_error = None

    try:
        soup = BeautifulSoup(svg_source, "html.parser")
        if _find_svg_tag(soup) is not None:
            return soup, None
        return None, "Не найден SVG-тэг после fallback-парсинга"
    except Exception as exc:
        if last_error is None:
            return None, f"Не получилось разобрать SVG: {exc}"
        return None, f"Не получилось разобрать SVG: {last_error}"


def _style_to_dict(style):
    values = {}
    for part in style.split(";"):
        part = part.strip()
        if not part or ":" not in part:
            continue
        key, value = part.split(":", 1)
        values[key.strip().lower()] = value.strip().lower().replace(" ", "")
    return values


def _is_target_group_style(style):
    if not style:
        return False

    style_dict = _style_to_dict(style)
    if style_dict.get("stroke") != "none":
        return False
    if style_dict.get("fill") not in {"#000", "#000000"}:
        return False

    fill_opacity = style_dict.get("fill-opacity")
    if fill_opacity is None:
        return False
    try:
        fill_opacity_value = float(fill_opacity)
    except ValueError:
        return False

    return abs(fill_opacity_value - 0.4) < 1e-9


def _is_target_group_attrs(g_tag):
    if g_tag.get("stroke") != "none":
        return False
    if g_tag.get("fill") not in {"#000", "#000000"}:
        return False

    fill_opacity = g_tag.get("fill-opacity")
    if fill_opacity is None:
        return False
    try:
        return abs(float(fill_opacity) - 0.4) < 1e-9
    except (TypeError, ValueError):
        return False


_PATH_TOKEN_RE = re.compile(
    r"[A-Za-z]|[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
)


def _path_anchor_signature(path_data):
    if not path_data:
        return None

    tokens = _PATH_TOKEN_RE.findall(path_data)
    if len(tokens) < 3 or tokens[0].lower() != "m":
        return None
    try:
        return round(float(tokens[1]), 1), round(float(tokens[2]), 1)
    except ValueError:
        return None


def _group_path_signature(g_tag):
    children = [child for child in g_tag.children if getattr(child, "name", None)]
    if not children or any(child.name != "path" for child in children):
        return None

    signatures = tuple(_path_anchor_signature(path.get("d")) for path in children)
    if any(signature is None for signature in signatures):
        return None
    return signatures


def _is_faint_duplicate_group(g_tag, target_signatures):
    paths = g_tag.find_all("path", recursive=False)
    if not paths:
        return False

    for path in paths:
        try:
            if abs(float(path.get("fill-opacity")) - 0.2) >= 1e-9:
                return False
        except (TypeError, ValueError):
            return False

    signature = _group_path_signature(g_tag)
    return signature is not None and signature in target_signatures

def is_orange(red, green, blue):

    hue, saturation, value = colorsys.rgb_to_hsv(
        red / 255,
        green / 255,
        blue / 255
    )

    hue = hue * 360

    return (
        10 <= hue <= 50
        and saturation >= 0.35
        and value >= 0.35
    )


def replace_hex_color(match, new_color):
    color = match.group(0)
    if len(color) == 4:
        red = int(color[1] * 2, 16)
        green = int(color[2] * 2, 16)
        blue = int(color[3] * 2, 16)
    else:
        red = int(color[1:3], 16)
        green = int(color[3:5], 16)
        blue = int(color[5:7], 16)

    if is_orange(red, green, blue):
        return new_color

    return color


def replace_rgb_color(match, new_color):
    red = int(match.group(1))
    green = int(match.group(2))
    blue = int(match.group(3))

    if is_orange(red, green, blue):
        return new_color

    return match.group(0)


def replace_orange_colors(text, new_color):
    if not isinstance(text, str):
        return text

    text = re.sub(
        r"\b(darkorange|orange|orangered)\b",
        new_color,
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b",
        lambda match: replace_hex_color(match, new_color),
        text
    )

    text = re.sub(
        r"rgb\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*\)",
        lambda match: replace_rgb_color(match, new_color),
        text,
        flags=re.IGNORECASE
    )

    return text

def restyle(soup, new_color):
    for tag in soup.find_all():
        for attribute_name in ("fill", "stroke", "color", "style"):
            if tag.has_attr(attribute_name):
                old_value = tag[attribute_name]
                new_value = replace_orange_colors(old_value, new_color)
                tag[attribute_name] = new_value

        if tag.name == "style" and tag.string:
            tag.string.replace_with(
                replace_orange_colors(str(tag.string), new_color)
            )
    return soup


def transform_svg_to_path(svg_source, out_file, new_color="#143B8F", file_id=None):
    soup, parse_error = _parse_svg_soup(svg_source)
    if soup is None:
        return [False, parse_error]

    if not is_svg(soup):
        return [False, "Это не SVG"]

    groups = list(soup.find_all("g"))
    total_g = len(groups)
    removed_g = 0
    target_signatures = set()

    # Первый проход: стандартный знак с opacity=0.4.
    for g in groups:
        if _is_target_group_style(g.get("style", "")) or _is_target_group_attrs(g):
            signature = _group_path_signature(g)
            if signature is not None:
                target_signatures.add(signature)
            g.decompose()
            removed_g += 1

    # Второй проход: более светлая копия того же набора path, встречающаяся
    # в некоторых исходниках рядом со стандартным знаком.
    for g in groups:
        if g.parent is not None and _is_faint_duplicate_group(g, target_signatures):
            g.decompose()
            removed_g += 1

    not_removed_g = total_g - removed_g

    comments = soup.find_all(string=lambda text: isinstance(text, Comment))
    removed_comments = len(comments)
    for comment in comments:
       comment.extract()

    soup = restyle(soup, new_color)

    out_file = Path(out_file)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_svg = out_file.with_suffix(".svg")
    try:
        out_svg.write_text(soup.prettify(), encoding="utf-8")
    except Exception as exc:
        return [False, f"Не получилось записать результат: {exc}"]

    display_id = file_id or out_file.stem

    return [
        True,
        (
            f"[{display_id}] Готово. "
            f"g: удалено={removed_g}, осталось={not_removed_g}. "
            f"Комментариев удалено={removed_comments}."
        ),
    ]
