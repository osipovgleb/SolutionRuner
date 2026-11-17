"""Read inherited SVG presentation without changing the original source asset."""

import re
from xml.etree import ElementTree as ET

from ..probability.common import UnsupportedCondition

NS = "{http://www.w3.org/2000/svg}"
PAINT = {
    "fill",
    "stroke",
    "stroke-width",
    "stroke-miterlimit",
    "stroke-linecap",
    "stroke-linejoin",
    "stroke-dasharray",
    "clip-path",
    "opacity",
    "fill-opacity",
    "stroke-opacity",
    "stop-color",
    "stop-opacity",
    "font-family",
    "font-size",
    "font-style",
    "font-weight",
    "text-anchor",
    "overflow",
}


def presentation(data):
    """Resolve only simple export classes and harmless paint declarations."""
    root = ET.fromstring(data)
    rules = {}
    styles = list(root.iter(NS + "style"))
    pattern = re.compile(r"\.([\w-]+)\s*\{([^{}]*)\}")

    def declarations(text):
        out = {}
        for item in text.split(";"):
            if not item.strip():
                continue
            name, value = map(str.strip, item.split(":", 1))
            if name == "enable-background":
                continue
            if name not in PAINT:
                raise UnsupportedCondition("unsupported native SVG presentation rule")
            if "url(" in value and not re.fullmatch(r"url\(#[\w-]+\)", value):
                raise UnsupportedCondition(
                    "only local SVG paint references are supported"
                )
            out[name] = value
        return out

    for style in styles:
        text = "".join(style.itertext())
        if pattern.sub("", text).strip():
            raise UnsupportedCondition("only simple SVG export classes are supported")
        for match in pattern.finditer(text):
            rules[match[1]] = declarations(match[2])

    def visit(node, inherited):
        attrs = {}
        for cls in node.get("class", "").split():
            if cls not in rules:
                raise UnsupportedCondition(
                    "the native SVG class has no paint definition"
                )
            attrs.update(rules[cls])
        attrs.update({k: v for k, v in node.attrib.items() if k in PAINT})
        attrs.update(declarations(node.attrib.pop("style", "")))
        for name in ("stroke", "fill"):
            if name not in attrs and name in inherited:
                attrs[name] = inherited[name]
        node.attrib.update(attrs)
        for child in list(node):
            if child.tag == NS + "style":
                node.remove(child)
            else:
                visit(child, attrs)

    visit(root, {})
    return ET.tostring(root, encoding="unicode")


def straight_segments(root):
    """Read straight axis/tangent strokes, including compact M/H/V paths."""
    result = []
    token = re.compile(r"[MmLlHhVv]|[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?")
    for node in root.iter():
        if node.tag == NS + "line":
            result.append(
                (node, tuple(float(node.get(k, 0)) for k in ("x1", "y1", "x2", "y2")))
            )
        elif node.tag == NS + "path":
            path = node.get("d", "")
            if re.sub(r"[\s,]", "", token.sub("", path)):
                continue  # Cubic curves and closed arrow heads are not lines.
            tokens = token.findall(path)
            current = (0.0, 0.0)
            command = None
            i = 0
            while i < len(tokens):
                if tokens[i].isalpha():
                    command = tokens[i]
                    i += 1
                if command is None:
                    raise UnsupportedCondition("invalid straight SVG stroke")
                count = 2 if command.lower() in ("m", "l") else 1
                values = list(map(float, tokens[i : i + count]))
                i += count
                if len(values) != count:
                    raise UnsupportedCondition("incomplete straight SVG stroke")
                x, y = current
                if command.lower() in ("m", "l"):
                    end = (
                        values[0] + (x if command.islower() else 0),
                        values[1] + (y if command.islower() else 0),
                    )
                elif command.lower() == "h":
                    end = (values[0] + (x if command.islower() else 0), y)
                else:
                    end = (x, values[0] + (y if command.islower() else 0))
                if command.lower() != "m":
                    result.append((node, (*current, *end)))
                else:
                    command = "l" if command.islower() else "L"
                current = end
    return result
