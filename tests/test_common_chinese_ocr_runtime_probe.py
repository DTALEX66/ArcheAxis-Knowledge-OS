"""Actual existing Chinese OCR resources; helper tests do not qualify candidate Core."""
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture
def probe(monkeypatch):
    def load(name,path):
        spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);monkeypatch.setitem(sys.modules,name,module);spec.loader.exec_module(module);return module
    load('aaos01_office_runtime_loop',ROOT/'scripts/probes/aaos01_office_runtime_loop.py')
    base_path=ROOT/'scripts/probes/aaos01_common_light_ocr_runtime_loop.py'
    # Isolated checkout retains an older base; only the declared main repository
    # is a permitted fallback. Merged tests import their own checkout normally.
    expected='bfdc7be40bdbc0991d1de2cbb3bb39714c3bd3c8b45c958dff64829a11058a80'
    if hashlib.sha256(base_path.read_bytes().replace(b'\r\n',b'\n')).hexdigest()!=expected:
        assert ROOT.parent.name=='worktrees' and ROOT.parent.parent.name=='.project-local'
        base_path=ROOT.parents[2]/'scripts/probes/aaos01_common_light_ocr_runtime_loop.py'
    assert hashlib.sha256(base_path.read_bytes().replace(b'\r\n',b'\n')).hexdigest()==expected,'Reviewed base preimage changed'
    load('aaos01_common_light_ocr_runtime_loop',base_path)
    m=load('chinese_ocr_probe',ROOT/'scripts/probes/aaos01_common_chinese_ocr_runtime_loop.py');m.load_worker=load;return m

def snapshot(result):
    outputs={'text':result['text'],'document_structure':json.dumps(result['structure'],ensure_ascii=False),'loss_report':json.dumps(result['loss_receipt'],ensure_ascii=False)}
    return {'job':{'status':200,'body':{'state':'succeeded','attempt':1}},'quality':{'status':200,'body':{}},**{key:{'status':200,'body':{'content':value,'metadata':{'sha256':hashlib.sha256(value.encode()).hexdigest(),'byte_length':len(value.encode())}}} for key,value in outputs.items()}}

@pytest.mark.skipif(os.environ.get('AAOS_EXECUTE_CHINESE_OCR')!='1',reason='NOT_EXECUTED: explicit existing Chinese OCR resource qualification')
@pytest.mark.parametrize('extension',['png','jpeg','scan'])
def test_actual_chinese_ocr_reads_png_jpeg_and_two_rendered_pdf_pages(probe,tmp_path,monkeypatch,extension):
    BINARY,DATA=probe.declared_ocr_resources()
    resources=probe.validate_chinese_resources(BINARY,DATA);assert resources['chi_sim']['bytes']>0
    generated=subprocess.run([sys.executable,'-B','-I','-c',probe.GENERATOR,str(tmp_path/'materials')],capture_output=True,text=True,encoding='utf-8',timeout=60);assert generated.returncode==0,generated.stderr
    monkeypatch.setenv('TESSERACT_CMD',str(BINARY));monkeypatch.setenv('TESSDATA_PREFIX',str(DATA));monkeypatch.setenv('ARCHEAXIS_OCR_TESSDATA',str(DATA))
    worker=probe.load_worker('actual_chinese_'+extension,ROOT/'services/python-workers/vision/worker_ocr.py')
    if extension=='scan':
        pdf=probe.load_worker('actual_chinese_scan_renderer',ROOT/'services/python-workers/document/worker_pdf.py')
        native=pdf.extract(str(tmp_path/'materials/complex.pdf'),ocr_dir=tmp_path/'rendered')
        assert not native['text'].strip() and native['loss_receipt']['params']['pages_without_text']==[1,2]
        candidates=native['loss_receipt']['params']['structure']['ocr_candidates'];assert len(candidates)==2
        inputs=[(tmp_path/'rendered'/page['file'],'扫描中文页一' if page['page']==1 else '扫描中文页二') for page in candidates]
        for page in candidates:
            assert hashlib.sha256((tmp_path/'rendered'/page['file']).read_bytes()).hexdigest()==page['sha256']
    else:inputs=[(tmp_path/f'materials/complex.{extension}','扫描中文页一')]
    evidence={'materials':'SYNTHETIC_AUTHORED','execution':'ACTUAL_LOCAL_PARSER_OCR','candidate_Core':'NOT_EXECUTED','resources':resources,'outputs':[]}
    for path,phrase in inputs:
        actual=worker.extract(path,'chi_sim',DATA);snap=snapshot(actual)
        probe.validate_outputs('png' if extension=='scan' else extension,snap,(phrase,))
        assert phrase in ''.join(actual['text'].split())
        source={'source_id':'protocol-helper-only','sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
        body=probe.ocr_page_body(source,'helper-job',snap) if phrase.endswith('二') else probe.location_body('png',source,'helper-job',snap,path.read_bytes())
        locator=json.loads(body['position']);assert locator['type']=='ocr_line' and locator['loss_sha256']==snap['loss_report']['body']['metadata']['sha256']
        assert '扫描中文页' in ''.join(actual['text'][locator['char_start']:locator['char_end']].split())
        # Reuse actual engine output for rejection controls, never invent a passing OCR result.
        evidence['outputs'].append({'input_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'input_bytes':path.stat().st_size,'phrase':phrase,'actual':json.loads(json.dumps(actual)),'locator_request':body})
        (tmp_path/'chinese-ocr-evidence.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')
        actual['loss_receipt']['params']['lang']='eng'
        with pytest.raises(AssertionError,match='English-only output'):probe.validate_outputs('png',snapshot(actual),(phrase,))


def test_chinese_probe_scope_does_not_promote_old_english_sentinel(probe):
    assert tuple(probe.KINDS)==('png','jpeg','pdf')
    assert probe.MARKERS['png']==('扫描中文页一',)
    assert "'ocr_languages_qualified':['chi_sim']" in probe.GENERATOR


def test_missing_exact_chinese_language_is_a_hard_failure(probe,tmp_path,monkeypatch):
    # Synthetic existence fixture, never executed as an OCR engine.
    monkeypatch.setattr(probe,'REPO',tmp_path)
    binary=tmp_path/'.project-local/engine/tesseract.exe';binary.parent.mkdir(parents=True);binary.write_bytes(b'not an engine')
    data=tmp_path/'.project-local/data';data.mkdir();(data/'eng.traineddata').write_bytes(b'not language data')
    with pytest.raises(AssertionError,match='Required Chinese OCR resource missing'):probe.validate_chinese_resources(binary,data)


@pytest.mark.parametrize('path',['E:/blocked/chi_sim','F:/blocked/engine','\\\\host/share/engine'])
def test_protected_resource_is_refused_before_resolve(probe,monkeypatch,path):
    def forbidden(*args,**kwargs):
        raise AssertionError('resolve must not be called')
    monkeypatch.setattr(Path,'resolve',forbidden)
    with pytest.raises(AssertionError,match='Protected OCR resource path'):
        probe.allowed_local_path(path)
