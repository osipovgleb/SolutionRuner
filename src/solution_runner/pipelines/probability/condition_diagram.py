"""Read one visible, checksum-verified condition diagram without changing it."""

import hashlib

from bs4 import BeautifulSoup

from .common import UnsupportedCondition, normalize, require_content


def read(
    context, evidence, assets_dir, *, identifiers=(), content_reader=require_content
):
    content = context.get("normalized_content") or {}
    sections = content.get("sections") or []
    condition = next((s for s in sections if s.get("key") == "condition"), None)
    if not condition or len(condition.get("asset_keys") or []) != 1:
        raise UnsupportedCondition("one audited condition diagram is required")
    key = condition["asset_keys"][0]
    assets = [a for a in content.get("assets", []) if a.get("asset_key") == key]
    if len(assets) != 1 or assets[0].get("asset_id") not in evidence:
        raise UnsupportedCondition(
            "the diagram needs an audited mathematical transcription"
        )
    asset = assets[0]
    entry = evidence[asset["asset_id"]]
    source = (
        assets_dir
        / entry.get("filename", asset["asset_id"] + entry.get("extension", ".svg"))
    ).read_bytes()
    if hashlib.sha256(source).hexdigest() != entry["sha256"]:
        raise UnsupportedCondition("the audited diagram template has changed")
    soup = BeautifulSoup(condition["html"], "html.parser")
    images = soup.find_all("img")
    if (
        len(images) != 1
        or images[0].get("data-asset-key") != key
        or images[0].get("data-asset-id") != asset["asset_id"]
    ):
        raise UnsupportedCondition("the visible diagram does not match its attachment")
    images[0].decompose()
    for node in soup.find_all("var"):
        if (
            set(node.attrs) != {"data-math-identifier"}
            or (len(node.get_text()) != 1 and node.get_text() not in identifiers)
            or node["data-math-identifier"] != node.get_text()
        ):
            raise UnsupportedCondition("unsupported mathematical identifier markup")
        node.unwrap()
    copied = {**condition, "html": str(soup), "asset_keys": []}
    clean = {
        **context,
        "normalized_content": {
            **content,
            "assets": [],
            "sections": [copied if s is condition else s for s in sections],
        },
    }
    _, _, answer, solution, text = content_reader(clean)
    return content, condition, answer, solution, normalize(text), entry, source


def verify_download(source, downloaded):
    if (
        not isinstance(downloaded, bytes)
        or hashlib.sha256(downloaded).digest() != hashlib.sha256(source).digest()
    ):
        raise UnsupportedCondition(
            "downloaded diagram bytes do not match the audited source"
        )
