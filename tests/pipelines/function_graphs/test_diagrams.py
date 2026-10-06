from fractions import Fraction
import hashlib
from xml.etree import ElementTree as ET

import pytest
from solution_runner.pipelines.function_graphs.diagrams import ASSET_DIR, registry, overlay_source_svg, svg_frame
NS={'svg':'http://www.w3.org/2000/svg'}

@pytest.mark.parametrize('key,graph',list(registry()['graphs'].items()))
def test_annotations_preserve_every_original_byte_and_use_matching_coordinates(key,graph):
    entry=next(e for e in registry()['conditions'].values() if e['graph_key']==key)
    source=(ASSET_DIR/entry['source_file']).read_bytes()
    for method,item in graph.items():
        data=(ASSET_DIR/item['file']).read_bytes()
        assert hashlib.sha256(data).hexdigest()==item['sha256']
        assert item['source_asset_id']
        if item.get('original'):
            assert data==source
            continue
        assert data==overlay_source_svg(source,entry['facts'],method,entry['kind'])
        start=data.index(b'<g data-role="hyperbola-solution-overlay">')
        end=data.index(b'</g>',start)+4
        assert data[:start]+data[end:]==source
        root=ET.fromstring(data);original=ET.fromstring(source)
        assert root.attrib==original.attrib
        assert [ET.tostring(n) for n in list(root)[:-1]]==[ET.tostring(n) for n in original]
        overlay=list(root)[-1]
        circles=overlay.findall('svg:circle',NS)
        assert len(circles)==(2 if method=='points' else 1)
        assert all(p.get('fill')=='#D12626' for p in circles)
        k,a,x,y=map(Fraction,entry['facts'])
        ox,oy,sx,sy,_=svg_frame(source)
        if method=='offset':
            ux,uy=map(Fraction,entry['offset_point'])
            assert ((ux+a)*uy if entry['kind']=='h' else ux*(uy-a))==k
            line=overlay.find('svg:line',NS)
            assert line.get('y1')==line.get('y2')==circles[0].get('cy')
            assert abs(float(line.get('x2'))-(ox+float(ux)*sx))<.001
            assert abs(float(line.get('y1'))-(oy-float(uy)*sy))<.001
        else:
            bx,by=map(Fraction,entry['second_point'])
            assert (k/(bx+a) if entry['kind']=='h' else k/bx+a)==by
            assert abs(float(circles[1].get('cx'))-(ox+float(bx)*sx))<.001
            assert abs(float(circles[1].get('cy'))-(oy-float(by)*sy))<.001


def test_runtime_reads_condition_mime_after_solution_assets_are_attached():
    from solution_runner.pipelines.core.content_runtime import _current_condition_asset_content_type
    class Gateway:
        def get_asset_metadata(self,asset_id):
            assert asset_id=='condition'
            return {'asset_id':asset_id,'content_type':'image/svg+xml'}
    ctx={'normalized_content':{'assets':[
        {'asset_key':'diagram','asset_id':'solution'},
        {'asset_key':'image_1','asset_id':'condition'}]}}
    assert _current_condition_asset_content_type(Gateway(),ctx,'hyperbola-shift-value')=='image/svg+xml'
