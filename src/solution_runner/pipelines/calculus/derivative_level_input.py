"""Read derivative-level problems and recover their source graphs."""

import hashlib
import io
import json
from copy import deepcopy
from fractions import Fraction
from functools import lru_cache
from pathlib import Path

from bs4 import BeautifulSoup
from PIL import Image

from ..equations.linear_system_intervals import Interval
from ..probability.common import UnsupportedCondition, normalize
from . import (
    derivative_level_curves,
    graph_derivative_levels,
    graph_input,
    graph_stationary,
    primitive_curves,
    raster_primitive,
)
from .derivative_level_geometry import _intersections, _model_entry, _native_entry


def _read(context):
    clean = deepcopy(context)
    content = clean["normalized_content"]
    condition = next(s for s in content["sections"] if s["key"] == "condition")
    if len(condition.get("asset_keys", [])) != 1:
        raise UnsupportedCondition("one derivative graph is required")
    asset = next(
        a for a in content["assets"] if a["asset_key"] == condition["asset_keys"][0]
    )
    soup = BeautifulSoup(condition["html"], "html.parser")
    images = soup.find_all("img")
    if len(images) != 1 or images[0].get("data-asset-id") != asset["asset_id"]:
        raise UnsupportedCondition("the visible derivative graph must match its asset")
    images[0].decompose()
    condition["html"] = str(soup)
    condition["asset_keys"] = []
    content["assets"] = []
    text = normalize(graph_input._read_text(clean)[4])
    text = text.replace(
        "график производной функции y=f'(x)— производной функции f(x)",
        "график производной функции f(x)",
    )
    text = text.replace(
        "график функции y=f'(x)— производной функции f(x)",
        "график производной функции f(x)",
    )
    text = text.replace(
        "график производной функции f'(x)", "график производной функции f(x)"
    )
    question = graph_derivative_levels.parse(text)
    if not question.count or question.domain is None:
        raise UnsupportedCondition(
            "an explicit interval and a derivative-level count are required"
        )
    domain = Interval(*map(Fraction, question.domain))
    trace_question = graph_stationary.Question(
        "count", domain, domain, horizontal=Fraction(question.slope)
    )
    return (
        question,
        trace_question,
        next(
            s
            for s in context["normalized_content"]["sections"]
            if s["key"] == "condition"
        ),
        asset,
    )


@lru_cache(maxsize=160)
def _recover(data, question):
    from .derivative_level_runner import CACHE

    digest = hashlib.sha256(data).hexdigest()
    if CACHE.exists():
        cached = json.loads(CACHE.read_text()).get(digest)
        if cached is not None:
            if cached["source_sha256"] != digest or cached["domain"] != [
                str(question.domain.lower),
                str(question.domain.upper),
            ]:
                raise UnsupportedCondition("the cached graph domain changed")
            primitive_curves.verify(cached)
            return cached
    png = data
    if data.startswith(b"\xff\xd8"):
        output = io.BytesIO()
        Image.open(io.BytesIO(data)).save(output, format="PNG")
        png = output.getvalue()
    model = derivative_level_curves.recover(png, question)
    model["source_sha256"] = digest
    return model


def _input(context, data):
    from .derivative_level_runner import CACHE

    q, trace_q, condition, asset = _read(context)
    model = None
    if data.startswith((raster_primitive.PNG, b"\xff\xd8")):
        model = deepcopy(_recover(data, trace_q))
    elif raster_primitive.META.encode() in data:
        canonical = data.replace("y = f′(x)".encode(), b"y = F(x)")
        model = raster_primitive.embedded(canonical, trace_q)
        cached = (
            json.loads(CACHE.read_text()).get(model["source_sha256"])
            if CACHE.exists()
            else None
        )
        if cached is not None:
            if cached["domain"] != model["domain"] or cached["span"] != model["span"]:
                raise UnsupportedCondition(
                    "the revised source graph has different intervals"
                )
            primitive_curves.verify(cached)
            model = deepcopy(cached)
    if model is not None:
        entry = _model_entry(model)
        points = _intersections(entry, q.slope)
    elif asset["asset_id"] in graph_input.EVIDENCE:
        parsed, q, entry, points, result = graph_derivative_levels._input(context)
        from ..probability import condition_diagram

        condition_diagram.verify_download(parsed[6], data)
        return q, condition, asset, entry, points, None, result
    else:
        entry = _native_entry(data, trace_q)
        points = _intersections(entry, q.slope)
    answer = next(
        (s for s in context["normalized_content"]["sections"] if s["key"] == "answer"),
        {},
    )
    stored = BeautifulSoup(answer.get("html", ""), "html.parser").get_text(strip=True)
    reviewed_path = (
        Path(__file__).with_name("assets") / "derivative-level-reviewed-counts.json"
    )
    reviews = json.loads(reviewed_path.read_text()) if reviewed_path.exists() else {}
    approved = reviews.get(
        model["source_sha256"]
        if model is not None
        else hashlib.sha256(data).hexdigest()
    )
    reviewed = (
        approved is not None
        and approved["domain"] == [str(x) for x in q.domain]
        and approved["slope"] == str(q.slope)
        and approved["count"] == len(points)
    )
    if (
        not reviewed
        and stored.isdigit()
        and str(int(stored)) == stored
        and int(stored) != len(points)
    ):
        raise UnsupportedCondition(
            f"the recovered level count {len(points)} differs from the stored answer {stored}; visual review is required"
        )
    return q, condition, asset, entry, points, model, str(len(points))
