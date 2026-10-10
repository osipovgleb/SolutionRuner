"""Verify exact solving, strict boundaries and deterministic diagram geometry."""
from fractions import Fraction
import xml.etree.ElementTree as ET

import pytest
from solution_runner.pipelines.equations.linear_system_intervals import parse_system, solve
from solution_runner.pipelines.equations.inequality_system_svg import render_intersection_svg


@pytest.mark.parametrize('rows, expected', [
    (r'x>3\\x<7', ('3', '7', False, False, False)),
    (r'x\ge3\\x\le7', ('3', '7', True, True, False)),
    (r'x>7\\x<3', (None, None, False, False, True)),
    (r'x<3\\x\le7', (None, '3', False, False, False)),
    (r'x>3\\x\ge7', ('7', None, True, False, False)),
    (r'x\ge3\\x\le3', ('3', '3', True, True, False)),
    (r'x>3\\x\le3', (None, None, False, False, True)),
    (r'-3x<-18\\5x-35<0', ('6', '7', False, False, False)),
    (r'x+4\ge-4{,}5\\x+4\le0', ('-17/2', '-4', True, True, False)),
])
def test_exact_intersections(rows, expected):
    """Check all direction combinations and equality/strict coincidence cases."""
    parsed = parse_system(r'\begin{cases}' + rows + r'\end{cases}')
    assert solve(parsed).key() == expected
    assert solve(tuple(reversed(parsed))).key() == expected


@pytest.mark.parametrize('left', ['<', '>', r'\le ', r'\ge '])
@pytest.mark.parametrize('right', ['<', '>', r'\le ', r'\ge '])
def test_svg_marks_each_source_endpoint_and_only_the_intersection(left, right):
    """Verify SVG endpoint fill and prevent blue hatching on an empty solution."""
    parsed = parse_system(r'\begin{cases}x' + left + r'3\\x' + right + r'7\end{cases}')
    svg = render_intersection_svg(parsed)
    root = ET.fromstring(svg)
    markers = [tag for tag in root.iter() if tag.get('data-inequality')]
    assert len(markers) == 2
    assert [tag.get('fill') == '#000000' for tag in markers] == [row.bound_relation.endswith('=') for row in parsed]
    arcs = [tag for tag in root.iter() if tag.get('data-half-line')]
    assert len(arcs) == 2
    for arc, row in zip(arcs, parsed):
        assert arc.get('d').endswith('H169.496' if row.bound_relation.startswith('>') else 'H9.873')
        assert ' A' not in arc.get('d')
    assert len([tag for tag in root.iter() if tag.get('data-half-line-arrow')]) == 2
    assert root.get('data-template-source-asset-id') == 'd2730267-5298-40ad-b8aa-870fad5f6f7e'
    assert float(root.get('width')) == pytest.approx(174.612)
    assert float(root.get('height')) == pytest.approx(52)
    assert any(tag.tag.endswith('polygon') and tag.get('points') == '169.405,48.581 163.399,44.081 178.412,48.581 163.399,53.081 ' for tag in root.iter())
    hatch = [tag for tag in root.iter() if tag.tag.endswith('line') and tag.get('stroke') == '#143B8F']
    assert bool(hatch) is not solve(parsed).empty
    assert not any('Пересечение пусто' in (tag.text or '') for tag in root.iter())
    assert svg == render_intersection_svg(parsed)


@pytest.mark.parametrize('expression', ['x*x', '__import__("os")', 'x^2', 'x/2'])
def test_unsupported_expressions_are_not_evaluated(expression):
    """Reject unsupported source syntax before any arithmetic or mutation."""
    with pytest.raises(ValueError):
        parse_system(r'\begin{cases}' + expression + r'<3\\x>0\end{cases}')


def test_solution_retains_systems_in_a_single_equivalence_chain():
    """Keep simultaneous transformations together in the reviewed parent style."""
    from bs4 import BeautifulSoup
    from solution_runner.pipelines.equations.linear_system_intervals import solution_html
    latex = r'\begin{cases}2x-3\le5\\7-3x\le1\end{cases}'
    rows = parse_system(latex)
    html = solution_html(latex, rows, solve(rows), '3')
    formulas = BeautifulSoup(html, 'html.parser').find_all('span', attrs={'data-inline-latex':True})
    assert len(formulas) == 1
    chain = formulas[0]['data-inline-latex']
    assert chain.count(r'\begin{cases}') == 3
    assert r'2x\le 8\\-3x\le -6' in chain
    assert r'x\le 4\\x\ge 2' in chain
    assert chain.endswith(r'2\le x\le 4')
