"""Read loan tables through the shared strict statistical-table grammar."""

from copy import deepcopy

from bs4 import BeautifulSoup, NavigableString

from ..statistics.common import read as read_tables
from .common import UnsupportedCondition, section


def read(context):
    content = context.get("normalized_content") or {}
    if any(s.get("asset_keys") for s in content.get("sections", [])):
        raise UnsupportedCondition(
            "debt schedules require sections without asset references"
        )
    original = tuple(
        section(content, key) for key in ("condition", "answer", "solution")
    )
    if original[0] is None:
        raise UnsupportedCondition("a canonical loan condition is required")
    prepared = deepcopy(context)
    condition = section(prepared["normalized_content"], "condition")
    soup = BeautifulSoup(condition["html"], "html.parser")
    for table in soup.find_all("table"):
        structure = {"table": {"tbody", "tr"}, "tbody": {"tr"}, "tr": {"th", "td"}}
        for tag in [table, *table.find_all(["tbody", "tr"])]:
            if any(
                (isinstance(child, NavigableString) and child.strip())
                or (
                    getattr(child, "name", None)
                    and child.name not in structure[tag.name]
                )
                for child in tag.children
            ):
                raise UnsupportedCondition(
                    "the debt table must contain only rows and cells"
                )
        for p in table.find_all("p"):
            if p.attrs or p.parent.name not in {"td", "th"}:
                raise UnsupportedCondition(
                    "only plain paragraph wrappers inside debt cells are supported"
                )
            p.insert_before(soup.new_string(" "))
            p.unwrap()
        for th in table.find_all("th"):
            if "data-valign" in th.attrs:
                if th["data-valign"] != "middle":
                    raise UnsupportedCondition("unsupported debt header alignment")
                del th["data-valign"]
        marker = soup.new_tag("p")
        marker.string = "ТАБЛИЦА"
        table.insert_before(marker)
    condition["html"] = str(soup)
    _, _, _, text, tables = read_tables(prepared)
    return *original, text, tables
