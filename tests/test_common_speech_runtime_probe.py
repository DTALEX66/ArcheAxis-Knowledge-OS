"""Real local offline speech/ASR checks, separately from candidate Core qualification."""
import importlib.util
import json
import os
import sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
MODEL=Path('D:/All projects/Model library/whisper/faster-whisper-large-v3-turbo')
FFMPEG=Path('D:/All projects/OS External Configuration/10-toolchains/scoop/apps/ffmpeg/current/bin/ffmpeg.exe')
POWERSHELL=Path('C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe')

@pytest.fixture
def probe(monkeypatch):
    def load(name,path):
        spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec)
        monkeypatch.setitem(sys.modules,name,module);spec.loader.exec_module(module);return module
    load('aaos01_office_runtime_loop',ROOT/'scripts/probes/aaos01_office_runtime_loop.py')
    load('aaos01_common_light_ocr_runtime_loop',ROOT/'scripts/probes/aaos01_common_light_ocr_runtime_loop.py')
    module=load('common_speech_probe',ROOT/'scripts/probes/aaos01_common_speech_runtime_loop.py');module.load_worker=load;return module

@pytest.fixture
def materials(probe,tmp_path):
    assert os.environ.get('AAOS_EXECUTE_LOCAL_ASR')=='1','Real model tests require explicit scoped local ASR qualification'
    probe.declared_model(MODEL)
    report=probe.generate_speech(tmp_path/'speech',POWERSHELL,FFMPEG)
    assert report['voice']['language']=='en-US'
    assert all(report['files'][ext]['bytes']>1000 for ext in ('wav','mp3','mp4'))
    return tmp_path/'speech'

@pytest.mark.skipif(os.environ.get('AAOS_EXECUTE_LOCAL_ASR')!='1',reason='NOT_EXECUTED: local ASR resource qualification needs explicit opt-in')
@pytest.mark.parametrize('extension',['wav','mp3','mp4'])
def test_actual_offline_spoken_content_is_decoded_by_existing_local_asr(probe,materials,tmp_path,monkeypatch,extension):
    monkeypatch.setenv('HF_HUB_OFFLINE','1');monkeypatch.setenv('TRANSFORMERS_OFFLINE','1')
    monkeypatch.setenv('FFMPEG_CMD',str(FFMPEG));monkeypatch.setenv('ARCHEAXIS_ASR_MODEL_DIR',str(MODEL))
    monkeypatch.setenv('ARCHEAXIS_CAPTION_PROTOCOL','disabled-for-audio-qualification')
    worker=probe.load_worker('actual_speech_'+extension,ROOT/'services/python-workers/media'/('worker_video.py' if extension=='mp4' else 'worker_transcribe.py'))
    if extension=='mp4':result=worker.extract_job(materials/'speech.mp4',tmp_path/'video',str(MODEL),'en','cpu')
    else:result=worker.extract(str(materials/f'speech.{extension}'),str(MODEL),'en','cpu')
    transport=probe.load_worker('speech_contract_'+extension,ROOT/'services/python-workers/transport/text_ndjson.py')
    result=transport._as_route_contract(result,'media.video' if extension=='mp4' else 'media.transcribe')
    def out(content):
        import hashlib
        return {'status':200,'body':{'content':content,'metadata':{'sha256':hashlib.sha256(content.encode()).hexdigest(),'byte_length':len(content.encode())}}}
    snap={'job':{'status':200,'body':{'state':'succeeded','attempt':1}},'quality':{'status':200,'body':{}},'text':out(result['text']),'document_structure':out(json.dumps(result['structure'])),'loss_report':out(json.dumps(result['loss_receipt']))}
    output=probe.validate_asr(extension,snap)
    assert output['cues'] and 'blue' in result['text'].lower()
    # The real decoder's output is reused for negative gate controls, never authored as OCR/ASR.
    bad_loss=json.loads(snap['loss_report']['body']['content'])
    bad_loss['params']['worker_output']['cues'][0]['end_ms']=output['duration_ms']+1
    snap['loss_report']=out(json.dumps(bad_loss))
    with pytest.raises(AssertionError):probe.validate_asr(extension,snap)


def test_model_path_cannot_silently_select_another_unregistered_model(probe,tmp_path):
    with pytest.raises(AssertionError):probe.declared_model(tmp_path)

def contract_snapshot(result):
    """Protocol fixture only: this is not an actual Core job receipt."""
    import hashlib
    def output(content):
        return {"status":200,"body":{"content":content,"metadata":{"sha256":hashlib.sha256(content.encode()).hexdigest(),"byte_length":len(content.encode())}}}
    return {"job":{"status":200,"body":{"state":"succeeded","attempt":1}},"quality":{"status":200,"body":{}},"text":output(result["text"]),"document_structure":output(json.dumps(result["structure"])),"loss_report":output(json.dumps(result["loss_receipt"]))}

@pytest.mark.parametrize("extension",["wav","mp4"])
def test_actual_header_worker_cannot_qualify_as_audio_content(probe,extension):
    worker=probe.load_worker("actual_header_"+extension,ROOT/"services/python-workers/document/worker_media.py")
    result=worker.extract(str(ROOT/"tests/fixtures/golden"/f"golden-{'audio' if extension=='wav' else 'video'}-anchor.{extension}"))
    transport=probe.load_worker("header_contract_"+extension,ROOT/"services/python-workers/transport/text_ndjson.py")
    result=transport._as_route_contract(result,"media.probe")
    with pytest.raises(AssertionError,match="Actual expected speech content missing"):
        probe.validate_asr(extension,contract_snapshot(result))


def test_time_locator_pins_actual_contract_cue_and_loss_fingerprint(probe):
    # Controlled cue protocol fixture exercises request construction, not ASR success.
    content=json.dumps({"params":{"worker_output":{"cues":[{"text":"blue circle","start_ms":120,"end_ms":910}]}}})
    snapshot={"job":{"body":{"attempt":3}},"loss_report":{"body":{"content":content,"metadata":{"sha256":"a"*64}}}}
    captured=[]
    def located(call,source,body):captured.append(body);return {"fixture":"request-construction-only"}
    original=probe.light.located
    try:
        probe.light.located=located
        probe.time_location(None,{"source_id":"owned","sha256":"b"*64},"job",snapshot)
    finally:probe.light.located=original
    locator=json.loads(captured[0]["position"])
    assert locator=={"type":"time","job_id":"job","attempt":3,"cue_index":0,"start_ms":120,"end_ms":910,"result_sha256":"a"*64}
    import hashlib
    assert captured[0]["checksum"]==hashlib.sha256(b"blue circle").hexdigest()


def test_selected_spoken_input_cannot_read_outside_project(probe,tmp_path):
    # Canonical root-run tmp_path is inside this project; use a lexical sibling
    # that is refused before any source file read (nothing is written there).
    outside = ROOT.parent / "unselected-speech-fixture"
    with pytest.raises(AssertionError,match="inside this project"):
        probe.generate_speech(tmp_path/"output",POWERSHELL,FFMPEG,outside/"speech.wav",outside/"truth.txt")

def test_owner_phrases_require_explicit_nonempty_truth_and_keep_unicode(probe):
    reference="今天的星环知识平台，保存原始证据。编号ＡＢ１２。"
    phrases=("星环知识平台", "原始证据", "ab12")
    assert probe.selected_phrases(reference,phrases,owner_input=True)==phrases
    assert probe.normalize_phrase(" 星 环，知识！ ")=="星环知识"
    assert probe.normalize_phrase("ＡＢ１２")=="ab12"
    for invalid in (None,[],[""],[" ！？ "],["不存在的句子"],["blue circle"]):
        with pytest.raises(AssertionError):probe.selected_phrases(reference,invalid,owner_input=True)
    assert probe.selected_phrases(probe.SPEECH)==probe.EXPECTED


def test_chinese_selected_time_anchor_uses_matching_cue_and_refuses_unlocated_phrase(probe):
    # Explicitly SYNTHETIC protocol fixture, never an ASR qualification result.
    cues=[{"text":"开场白","start_ms":100,"end_ms":700},
          {"text":"星环知识平台，保留原始证据。","start_ms":750,"end_ms":1800}]
    snapshot={"job":{"body":{"attempt":2}},"loss_report":{"body":{"content":json.dumps({"params":{"worker_output":{"cues":cues}}},ensure_ascii=False),"metadata":{"sha256":"c"*64}}}}
    captured=[]
    original=probe.light.located
    def fixture(call,source,body):captured.append(body);return {"scope":"SYNTHETIC_REQUEST_CONSTRUCTION_ONLY"}
    try:
        probe.light.located=fixture
        result=probe.time_location(None,{"source_id":"owned","sha256":"d"*64},"actual-cue-contract",snapshot,("原始证据",))
        assert result["matched_phrase"]=="原始证据"
        position=json.loads(captured[0]["position"])
        assert position["cue_index"]==1 and position["start_ms"]==750 and position["end_ms"]==1800
        with pytest.raises(AssertionError,match="single actually located cue"):
            probe.time_location(None,{"source_id":"owned","sha256":"d"*64},"job",snapshot,("不存在",))
        # Phrases crossing two independently timed cues cannot invent a combined time range.
        with pytest.raises(AssertionError,match="single actually located cue"):
            probe.time_location(None,{"source_id":"owned","sha256":"d"*64},"job",snapshot,("开场白星环知识平台",))
    finally:probe.light.located=original


@pytest.mark.parametrize("extension",["wav","mp4"])
def test_actual_header_worker_cannot_satisfy_chinese_selected_phrase(probe,extension):
    worker=probe.load_worker("actual_header_unicode_"+extension,ROOT/"services/python-workers/document/worker_media.py")
    result=worker.extract(str(ROOT/"tests/fixtures/golden"/f"golden-{'audio' if extension=='wav' else 'video'}-anchor.{extension}"))
    transport=probe.load_worker("header_unicode_contract_"+extension,ROOT/"services/python-workers/transport/text_ndjson.py")
    result=transport._as_route_contract(result,"media.probe")
    with pytest.raises(AssertionError,match="Actual expected speech content missing"):
        probe.validate_asr(extension,contract_snapshot(result),("星环知识平台",))
