"""Correct the source's K label to the F explicitly named in the condition."""

import xml.etree.ElementTree as ET
from copy import deepcopy

from ..core.errors import ContentPlanError
from .distance_sources import source_bytes

SOURCE = "8e8e20aa-04ee-4513-8a9c-4a84ca87ab46"
LETTER_SOURCE = "cb43c350-1e5c-4ce3-b113-8cfb8cdcc85c"


def render(m):
    if m.mode != "trapezoid_prism_pentagon_area" or m.names != ("G", "F"):
        raise ContentPlanError("the reviewed relabelling requires the G/F pentagon")
    root = ET.fromstring(source_bytes(SOURCE))
    letters = ET.fromstring(source_bytes(LETTER_SOURCE))
    letter = deepcopy(letters[11])
    letter.set("id", "label-F")
    letter.set("transform", "translate(65.7495 -83.824)")
    root.remove(root[30])
    root.insert(30, letter)
    return ET.tostring(root, encoding="unicode")
