"""Bounded language preparation and fail-closed Chinese CI wiring; no network/install."""
import hashlib
import importlib.util
from pathlib import Path
import pytest
import yaml
ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture
def prepare():
    spec=importlib.util.spec_from_file_location('prepare_windows_chinese',ROOT/'scripts/ci/prepare_windows_ocr.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def test_chinese_pin_has_official_versioned_source_and_measured_local_identity(prepare):
    pin=prepare.language_pins(True)
    assert set(pin)=={'eng','chi_sim'}
    assert pin['chi_sim']=={'url':'https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/4.1.0/chi_sim.traineddata','sha256':'a5fcb6f0db1e1d6d8522f39db4e848f05984669172e584e8d76b6b3141e1f730','bytes':2469156}
    assert set(prepare.language_pins())=={'eng'}


def synthetic_download(prepare,monkeypatch):
    payloads={'eng':b'synthetic English language bytes','chi_sim':b'synthetic Chinese language bytes'}
    pin=dict(prepare.PIN)
    for name,raw in payloads.items():
        pin.update({name+'_url':'https://raw.githubusercontent.com/fixture/'+name,name+'_sha256':hashlib.sha256(raw).hexdigest(),name+'_bytes':len(raw)})
    monkeypatch.setattr(prepare,'PIN',pin)
    calls=[]
    def download(url,path,expected,maximum):
        name=path.stem;calls.append(name);path.write_bytes(payloads[name])
    monkeypatch.setattr(prepare,'download',download)
    return payloads,calls


def test_preparation_preserves_english_and_adds_exact_chinese(prepare,monkeypatch,tmp_path):
    _,calls=synthetic_download(prepare,monkeypatch)
    assets=prepare.prepare_languages(tmp_path,True)
    assert calls==['eng','chi_sim'] and set(assets)=={'eng','chi_sim'}
    prepare.require_languages('List of available languages (2):\neng\nchi_sim\n',assets)


@pytest.mark.parametrize('damage',['wrong_bytes','wrong_hash'])
def test_downloaded_language_cannot_pass_wrong_identity(prepare,monkeypatch,tmp_path,damage):
    synthetic_download(prepare,monkeypatch)
    if damage=='wrong_bytes':prepare.PIN['chi_sim_bytes']+=1
    else:prepare.PIN['chi_sim_sha256']='0'*64
    with pytest.raises(ValueError,match='Language data bytes/SHA mismatch: chi_sim'):
        prepare.prepare_languages(tmp_path,True)


@pytest.mark.parametrize('listing',['eng\n','eng\nchi_sim_vert\n'])
def test_english_or_vertical_chinese_does_not_qualify_required_chinese(prepare,listing):
    with pytest.raises(ValueError,match='Required OCR language not available: chi_sim'):
        prepare.require_languages(listing,('eng','chi_sim'))


def test_desktop_fast_requires_chinese_core_probe_and_keeps_english_baseline():
    jobs=yaml.safe_load((ROOT/'.github/workflows/ci.yml').read_text())['jobs']
    steps=jobs['desktop-fast']['steps']
    prep=next(step for step in steps if step.get('id')=='common_ocr_tools')
    assert '--require-chinese' in prep['run']
    english=next(step for step in steps if step.get('id')=='common_light_ocr_loop')
    chinese=next(step for step in steps if step.get('id')=='common_chinese_ocr_loop')
    assert steps.index(english)<steps.index(chinese)
    assert 'common_chinese_ocr_runtime_loop.py' in chinese['run'] and '--tessdata $env:ARCHEAXIS_OCR_TESSDATA' in chinese['run']
    assert not chinese.get('continue-on-error') and 'if' not in chinese
    upload=next(step for step in steps if step.get('name')=='Upload common light and OCR qualification evidence')
    assert 'common-chinese-ocr.json' in upload['with']['path']
    other_preps=[step['run'] for job in jobs.values() for step in job.get('steps',[]) if 'prepare_windows_ocr.py' in step.get('run','') and step.get('id')!='common_ocr_tools']
    assert all('--require-chinese' not in command for command in other_preps)
