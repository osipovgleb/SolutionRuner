from pathlib import Path
from xml.etree import ElementTree as ET

from solution_runner.pipelines.core.group_profiles import get_group_profile


ASSET_DIR = (
    Path(__file__).parents[3]
    / "src/solution_runner/pipelines/equations/assets/trigonometry"
)
NS = {"svg": "http://www.w3.org/2000/svg"}


def _root(name: str):
    return ET.parse(ASSET_DIR / name).getroot()


def test_all_current_corpus_value_assets_are_static_and_xml_valid():
    files = sorted(ASSET_DIR.glob("*.svg"))
    assert len(files) == 17
    for path in files:
        root = ET.parse(path).getroot()
        assert root.findall(".//svg:defs", NS) == []
        assert root.findall(".//svg:path", NS) == []
        assert root.findall(".//svg:clipPath", NS) == []
        labels = root.findall(".//svg:text", NS)
        assert labels
        assert all(
            label.get("font-family") == "Liberation Sans, DejaVu Sans, sans-serif"
            for label in labels
        )
        assert all("α" not in "".join(label.itertext()) for label in labels)


EXPECTED_ANGLES = {
    "cos-half.svg": {"π/3", "5π/3"},
    "cos-sqrt2-over-2.svg": {"π/4", "7π/4"},
    "cos-sqrt3-over-2.svg": {"π/6", "11π/6"},
    "sin-minus-one.svg": {"3π/2"},
    "sin-minus-sqrt3-over-2.svg": {"4π/3", "5π/3"},
    "sin-minus-sqrt2-over-2.svg": {"5π/4", "7π/4"},
    "sin-minus-half.svg": {"7π/6", "11π/6"},
    "sin-half.svg": {"π/6", "5π/6"},
    "sin-sqrt2-over-2.svg": {"π/4", "3π/4"},
    "sin-sqrt3-over-2.svg": {"π/3", "2π/3"},
    "sin-one.svg": {"π/2"},
    "tg-minus-sqrt3.svg": {"5π/3"},
    "tg-minus-one.svg": {"7π/4"},
    "tg-minus-one-over-sqrt3.svg": {"11π/6"},
    "tg-one-over-sqrt3.svg": {"π/6"},
    "tg-one.svg": {"π/4"},
    "tg-sqrt3.svg": {"π/3"},
}


def _text_values(name: str) -> set[str]:
    return {
        "".join(element.itertext())
        for element in _root(name).findall(".//svg:text", NS)
    }


def test_every_intersection_has_a_concrete_angle_and_axes_are_named():
    assert set(path.name for path in ASSET_DIR.glob("*.svg")) == set(EXPECTED_ANGLES)
    for name, angles in EXPECTED_ANGLES.items():
        values = _text_values(name)
        assert angles <= values
        assert {"sin", "cos"} <= values
        if name.startswith("tg-"):
            assert "tg" in values


def test_cos_assets_have_only_a_vertical_blue_dashed_chord():
    for path in ASSET_DIR.glob("cos-*.svg"):
        lines = [
            line
            for line in _root(path.name).findall(".//svg:line", NS)
            if line.get("stroke") == "#00487E"
        ]
        assert len(lines) == 1
        line = lines[0]
        assert line.get("x1") == line.get("x2")
        assert line.get("stroke-dasharray") == "5,3"


def test_sin_assets_have_only_a_horizontal_blue_dashed_chord():
    for path in ASSET_DIR.glob("sin-*.svg"):
        lines = [
            line
            for line in _root(path.name).findall(".//svg:line", NS)
            if line.get("stroke") == "#00487E"
        ]
        assert len(lines) == 1
        line = lines[0]
        assert line.get("y1") == line.get("y2")
        assert line.get("stroke-dasharray") == "5,3"


def test_tangent_assets_have_a_single_blue_dashed_control_segment():
    for path in ASSET_DIR.glob("tg-*.svg"):
        lines = [
            line
            for line in _root(path.name).findall(".//svg:line", NS)
            if line.get("stroke") == "#00487E"
        ]
        assert len(lines) == 1
        line = lines[0]
        assert line.get("stroke-dasharray") == "5,3"
        assert (line.get("x1"), line.get("y1")) != ("76", "109.5")
        assert line.get("x2") == "132"


def test_all_three_groups_use_one_registered_trigonometric_rule():
    profiles = [get_group_profile(key) for key in ("26669", "77376", "77377")]
    assert {profile.content_rule_key for profile in profiles} == {
        "trigonometric-table-value-affine-argument"
    }
