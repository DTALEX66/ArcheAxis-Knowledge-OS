"""Real local parser/helper checks; no candidate Core or OCR accuracy claim."""
import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture
def probe(monkeypatch):
    def load(name,path):
        spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec)
        monkeypatch.setitem(sys.modules,name,module);spec.loader.exec_module(module);return module
    load('aaos01_office_runtime_loop',ROOT/'scripts/probes/aaos01_office_runtime_loop.py')
    m=load('common_light_ocr_probe',ROOT/'scripts/probes/aaos01_common_light_ocr_runtime_loop.py');m.load_worker=load;return m

@pytest.fixture
def materials(probe,tmp_path):
    out=tmp_path/'materials';result=subprocess.run([sys.executable,'-B','-I','-c',probe.GENERATOR,str(out)],capture_output=True,text=True,encoding='utf-8',timeout=60)
    assert result.returncode==0,result.stderr
    return out

def snapshot(result):
    contents={'text':result['text'],'document_structure':json.dumps(result['structure'],ensure_ascii=False),'loss_report':json.dumps(result['loss_receipt'],ensure_ascii=False)}
    return {'job':{'status':200,'body':{'state':'succeeded','attempt':1}},'quality':{'status':200,'body':{}},**{key:{'status':200,'body':{'content':body,'metadata':{'sha256':hashlib.sha256(body.encode()).hexdigest(),'byte_length':len(body.encode())}}} for key,body in contents.items()}}

@pytest.mark.parametrize('extension',['txt','md','csv','json','html','srt','vtt','canvas'])
def test_actual_chinese_light_parsers_and_locator_selection(probe,materials,extension):
    transport=probe.load_worker('light_actual_transport_'+extension,ROOT/'services/python-workers/transport/text_ndjson.py')
    route=('web','worker_html.py') if extension=='html' else ('document','worker_subtitles.py') if extension in ('srt','vtt') else ('document','worker_canvas.py') if extension=='canvas' else ('document','worker_text.py')
    worker=probe.load_worker('light_actual_'+extension,ROOT/'services/python-workers'/route[0]/route[1])
    path=materials/f'complex.{extension}'
    if extension in ('txt','md','csv','json'):
        result=worker.extract(str(path),{'txt':'text/plain','md':'text/markdown','csv':'text/csv','json':'application/json'}[extension])
    else:
        result=transport._as_route_contract(worker.extract(str(path)),probe.KINDS[extension])
    snap=snapshot(result);text,loss=probe.validate_outputs(extension,snap)
    assert '中文' in text
    source={'source_id':'authored','sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    body=probe.location_body(extension,source,'actual-helper-job',snap,path.read_bytes())
    locator=json.loads(body['position']);assert body['checksum']!='0'*64
    assert locator['type']==('text' if extension in ('txt','md') else 'format_location' if extension in ('csv','json') else 'worker_structure')
    if extension=='txt':
        raw=path.read_bytes();assert text==raw.decode('utf-8')
        assert raw[locator['start']:locator['end']]=='末尾证据'.encode('utf-8')
        assert body['checksum']==hashlib.sha256('末尾证据'.encode('utf-8')).hexdigest()
    bad=copy.deepcopy(snap);bad['text']['body']['metadata']['sha256']='0'*64
    with pytest.raises(AssertionError): probe.validate_outputs(extension,bad)
    bad=copy.deepcopy(snap);bad['job']['body']['state']='failed'
    with pytest.raises(AssertionError): probe.validate_outputs(extension,bad)


def test_generated_scan_has_two_actual_image_only_chinese_source_pages(probe,materials):
    import fitz
    from PIL import Image
    with fitz.open(materials/'complex.pdf') as doc:
        assert len(doc)==2
        assert all(not page.get_text().strip() and len(page.get_images())==1 for page in doc)
        pix=doc[0].get_pixmap();assert pix.width>0 and pix.height>0
    for extension in ('png','jpeg'):
        with Image.open(materials/f'complex.{extension}') as image:
            assert image.width>1000 and image.height>300
    # No OCR output is invented here; candidate probe must execute actual image.ocr.


def test_resolver_refusal_is_a_hard_qualification_failure(probe):
    def call(method,path,body=None,expected=200):
        if method=='POST':return {'location_status':'located','anchor_id':'anchor'}
        return {'status':'STALE','scope':'locator_provenance_only'}
    with pytest.raises(AssertionError):probe.located(call,{'source_id':'owned'}, {'checksum':'a'*64})

@pytest.mark.parametrize("suffix,media,separator",[("csv","text/csv",","),("tsv","text/tab-separated-values","\t")])
def test_native_facts_merge_retains_cell_path_and_multi_letter_coordinate(probe,tmp_path,suffix,media,separator):
    worker=probe.load_worker("actual_cell_merge_"+suffix,ROOT/"services/python-workers/document/worker_text.py")
    rows=[[f"字段{i}" for i in range(28)],[f"中文{i}" for i in range(28)]]
    path=tmp_path/f"cells.{suffix}";path.write_text("\n".join(separator.join(row) for row in rows),encoding="utf-8")
    result=worker.extract(str(path),media)
    locations=result["loss_receipt"]["params"]["format"]["locations"]
    last=next(item for item in locations if item["row"]==2 and item["column"]==28)
    assert last["coordinate"]=="AB2" and last["path"]==f"{suffix}!AB2" and last["value"]=="中文27"
    assert result["text"]==path.read_bytes().decode("utf-8")


def test_deduplicated_image_and_pdf_page_freeze_final_anchors_without_losing_history(probe):
    image_anchor={'anchor_id':'image-original','position':'original'}
    page_anchor={'anchor_id':'pdf-page','position':'page'}
    calls=[]
    def call(method,path):
        calls.append((method,path))
        return {'anchors':[image_anchor,page_anchor]}
    records=[{'anchors':{'same-source':{'anchors':[image_anchor]}}},
             {'anchors':{'same-source':{'anchors':[image_anchor,page_anchor]}}}]
    assert probe.final_anchor_snapshots(call,records)=={'same-source':{'anchors':[image_anchor,page_anchor]}}
    assert calls==[('GET','/api/v1/sources/same-source/anchors')]
    with pytest.raises(AssertionError,match='historical anchor disappeared'):
        probe.final_anchor_snapshots(lambda *_:{'anchors':[page_anchor]},records)
