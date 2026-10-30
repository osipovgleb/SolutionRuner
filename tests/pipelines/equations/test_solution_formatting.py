import pytest
from bs4 import BeautifulSoup

from solution_runner.pipelines.equations.solution_formatting import vertical_derivation


def test_splits_only_outer_equivalences_and_preserves_prose_and_math():
    formula = r"x=1\iff \begin{cases}x=1\iff x^2=1\\x>0\end{cases}\iff x=1"
    source = (
        '<p>Пояснение.</p><center><p><span data-inline-latex="'
        + formula
        + '"></span>.</p></center>'
    )
    result = vertical_derivation(source)
    soup = BeautifulSoup(result, "html.parser")
    assert [s["data-inline-latex"] for s in soup.select("span")] == [
        "x=1",
        r"\begin{cases}x=1\iff x^2=1\\x>0\end{cases}",
        "x=1",
    ]
    assert soup.find("p").get_text() == "Пояснение."
    assert vertical_derivation(result) == result


def test_preserves_inline_formulas_in_prose():
    source = '<p>Имеем <span data-inline-latex="x=1\\iff x^2=1"></span> при x&gt;0.</p>'
    assert vertical_derivation(source) == source


@pytest.mark.parametrize(
    "formula", [r"x=1\iff \begin{cases}x=1", r"x=1\iff \frac{1}{2", r"x=1\iff "]
)
def test_rejects_malformed_generated_derivations(formula):
    with pytest.raises(ValueError):
        vertical_derivation(
            '<center><p><span data-inline-latex="' + formula + '"></span>.</p></center>'
        )
