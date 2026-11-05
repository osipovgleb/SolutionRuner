"""Read complete orthogonal element fixtures and their reviewed parent constructions."""

import json
from pathlib import Path

from solution_runner.pipelines.solids.orthogonal_element_model import read
from solution_runner.pipelines.solids.orthogonal_element_sources import DATA

FIXTURE = json.loads(
    (
        Path(__file__).parent / "fixtures/category_3_orthogonal_element_sources.json"
    ).read_text()
)
CASES = FIXTURE["cases"]
BOUND = [c for c in CASES if "pending_reason" not in c]
PENDING = [c for c in CASES if "pending_reason" in c]


def model(case):
    review = DATA["proofs"][
        case["source"] + ":" + case["mode"] + ":" + case["requested"]
    ]
    return read(case["source"], case["mode"], case["requested"], review["method"])
