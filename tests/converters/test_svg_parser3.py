from pathlib import Path

from bs4 import BeautifulSoup

from solution_runner.converters import svg_parser3


def test_transform_removes_both_copies_of_duplicate_watermark(tmp_path: Path):
    source = """\
<svg xmlns="http://www.w3.org/2000/svg">
  <g id="faint-watermark">
    <path fill-opacity="0.2" d="M138.1,188.9c0,0.8,0,1.6,0,2.5C136.799,189.1,137.499,187.4,137.4,186.6"/>
    <path fill-opacity="0.2" d="M147,187c-0.399,0.8-1.899,0.102-2.8,0.3C142.2,187.2,144.5,189.7,145.7,188.8"/>
  </g>
  <g id="drawing">
    <path fill-opacity="0.2" d="M 1,1 L 9,9"/>
  </g>
  <g style="stroke:none; fill:#000; fill-opacity:0.4">
    <path d="m 138.1,188.9 c 0,0.8 0,1.6 0,2.5 -1.3,0.2 -0.6,-1.5 -0.7,-2.3"/>
    <path d="m 147.0,187.0 c -0.4,0.8 -1.9,0.1 -2.8,0.3 -2.0,-0.1 0.3,2.4 1.5,1.5"/>
  </g>
</svg>
"""

    status, _ = svg_parser3.transform_svg_to_path(
        source,
        tmp_path / "cleaned",
        file_id="duplicate-watermark",
    )

    assert status is True
    result = BeautifulSoup(
        (tmp_path / "cleaned.svg").read_text(encoding="utf-8"),
        "xml",
    )
    assert result.find("g", id="faint-watermark") is None
    assert result.find("g", id="drawing") is not None
    assert len(result.find_all("g")) == 1
