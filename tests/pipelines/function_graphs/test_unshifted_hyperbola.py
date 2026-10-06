from copy import deepcopy
import hashlib,json
from pathlib import Path
import pytest
from bs4 import BeautifulSoup
from solution_runner.pipelines.core.content_runtime import _with_required_assets
from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.function_graphs.unshifted_hyperbola import ASSET_DIR,registry,annotate,build_context_repair_plan
FIXTURES=Path(__file__).parent/'fixtures'
def ctx(n):return _with_required_assets(json.loads((FIXTURES/f'{n}.json').read_text()),'hyperbola-unshifted-value')
def plan(c,n):return build_context_repair_plan(c,condition_asset_bytes=(FIXTURES/f'{n}.svg').read_bytes(),current_asset_content_type='image/svg+xml')
def materialize(c,changes):
 c=deepcopy(c)
 for t in changes:
  key=t['transformation_target_id'].split(':')[1];section=next(s for s in c['normalized_content']['sections'] if s['key']==key);section.update(t['value'])
 return c
@pytest.mark.parametrize('n,expected',[(660801,'0,1'),(685371,'0,1'),(704625,'0,5')])
def test_one_unknown_two_methods_preserve_condition_and_repeat(n,expected):
 c=ctx(n);before=deepcopy(c);p=plan(c,n);assert c==before and p.answer==expected and not p.warnings
 updated=materialize(c,p.transformations)
 assert next(s for s in updated['normalized_content']['sections'] if s['key']=='condition')==next(s for s in before['normalized_content']['sections'] if s['key']=='condition')
 html=next(s['html'] for s in updated['normalized_content']['sections'] if s['key']=='solution');soup=BeautifulSoup(html,'html.parser')
 assert len(soup.select('section[data-content-kind="solution"]'))==2 and len(soup.find_all('img'))==2
 assert 'Возьмём точку' in soup.get_text() and 'две точки' not in soup.get_text()
 assert r'\begin{cases}' not in html and r'\frac{k}{x}' in html
 assert not plan(updated,n).transformations
@pytest.mark.parametrize('aid,e',list(registry()['conditions'].items()))
def test_svg_annotations_only_append_to_original(aid,e):
 if e['content_type']!='image/svg+xml':return
 data=(ASSET_DIR/e['source_file']).read_bytes();assert hashlib.sha256(data).hexdigest()==e['sha256']
 for method in ('points','offset'):
  out=(ASSET_DIR/e[method]['file']).read_bytes();assert out==annotate(data,e,method)
  start=out.index(b'<g data-role="unshifted-hyperbola-overlay">');end=out.index(b'</g>',start)+4
  assert out[:start]+out[end:]==data
  assert (b'<line ' in out[start:end])==(method=='offset')
def test_unregistered_geometry_and_zero_argument_fail_closed():
 c=ctx(660801)
 with pytest.raises(ContentPlanError,match='bytes differ'):
  build_context_repair_plan(c,condition_asset_bytes=(FIXTURES/'660801.svg').read_bytes()+b' ',current_asset_content_type='image/svg+xml')
 condition=next(s for s in c['normalized_content']['sections'] if s['key']=='condition');condition['html']=condition['html'].replace('(10)','(0)')
 with pytest.raises(ContentPlanError,match='nonzero'):plan(c,660801)
def test_audited_png_warns_without_stopping_or_changing_graph():
 c=json.loads((FIXTURES/'704625-raster.json').read_text());p=build_context_repair_plan(c,condition_asset_bytes=(FIXTURES/'704625.png').read_bytes(),current_asset_content_type='image/png')
 assert p.answer=='0,5' and p.warnings
 assert all(t['transformation_target_id'].startswith('section:solution') for t in p.transformations)
 assert 'красный отрезок' not in p.transformations[0]['value']['html']
