"""Chinese candidate OCR qualification extending the verified English/light probe.

English sentinel qualification remains separate. This wrapper qualifies actual
Chinese phrases only, with the existing native OCR locator contract.
"""
from __future__ import annotations
import argparse
import contextlib
import hashlib
import io
import json
import os
import sys
from pathlib import Path, PureWindowsPath
import aaos01_common_light_ocr_runtime_loop as base
REPO=Path(__file__).resolve().parents[2]
# Git stores LF; Windows checkouts may use CRLF. Normalize only line endings.
BASE_PREIMAGE='bfdc7be40bdbc0991d1de2cbb3bb39714c3bd3c8b45c958dff64829a11058a80'
KINDS={'png':'image','jpeg':'image','pdf':'pdf'}
MARKERS={'png':('扫描中文页一',),'jpeg':('扫描中文页一',)}
GENERATOR=base.GENERATOR.replace("'ocr_languages_qualified':['eng'],'chinese_scan_recognition':'UNMEASURED'", "'ocr_languages_qualified':['chi_sim'],'recognition_accuracy':'UNMEASURED'")
verify_artifacts=base.verify_artifacts
_BASE_VALIDATE=base.validate_outputs


def allowed_local_path(value):
    # Lexical refusal precedes resolve/stat so protected drives are never visited.
    raw=str(value)
    windows=PureWindowsPath(raw)
    assert windows.drive.casefold() not in ('e:','f:') and not raw.startswith(('\\\\','//')),'Protected OCR resource path'
    result=Path(value).resolve()
    assert result.drive.casefold() not in ('e:','f:') and not str(result).startswith('\\\\'),'Protected OCR resource target'
    return result


def declared_ocr_resources():
    resolver=base.office.load('chinese_ocr_tool_paths',REPO/'services/python-workers/tool_paths.py')
    # Read only the project declaration, never an arbitrary manifest override.
    resolver._manifest_path=lambda:REPO/'config/environment/capability-requirements.yaml'
    root_text=next((os.environ[key].strip() for key in ('OS_EXTERNAL_CONFIG','ARCHEAXIS_EXTERNAL_ROOT') if os.environ.get(key,'').strip()),None)
    if root_text is None:
        index=REPO/'config/environment/external-resources-index.json'
        root_text=json.loads(index.read_text(encoding='utf-8')).get('external_root')
    assert isinstance(root_text,str) and root_text.strip(),'Declared OCR external root missing'
    root=allowed_local_path(root_text)
    binary=resolver.declared_location('tesseract',root=root)
    data=resolver.declared_location('tesseract-languages',root=root)
    assert binary and data,'Declared OCR engine or language directory missing'
    return allowed_local_path(binary),allowed_local_path(data)


def validate_chinese_resources(binary,tessdata):
    binary=allowed_local_path(binary);tessdata=allowed_local_path(tessdata)
    prepared=binary.is_relative_to(REPO/'.project-local') and tessdata.is_relative_to(REPO/'.project-local')
    if not prepared:
        exact_binary,exact_data=declared_ocr_resources()
        assert binary==exact_binary and tessdata==exact_data,'OCR resources must be declared exact assets or project-owned prepared assets'
    result={}
    for name,file in (('binary',binary),('chi_sim',tessdata/'chi_sim.traineddata')):
        assert file.is_file() and file.stat().st_size>0,f'Required Chinese OCR resource missing: {name}'
        result[name]={'path':str(file),'bytes':file.stat().st_size,'sha256':hashlib.sha256(file.read_bytes()).hexdigest()}
    return result


def validate_outputs(extension,snapshot,expected=None):
    if extension in ('png','jpeg'):
        # The base scan branch passes its English page sentinel. Select the known
        # Chinese phrase for the same authored page; never turn English into Chinese evidence.
        phrase='扫描中文页二' if expected and ('TWO' in expected[0] or expected[0].endswith('二')) else '扫描中文页一'
        result=_BASE_VALIDATE(extension,snapshot,(phrase,))
        assert result[1]['params']['lang']=='chi_sim','English-only output cannot qualify Chinese OCR'
        return result
    return _BASE_VALIDATE(extension,snapshot,expected)


def location_body(extension,source,job,snapshot,raw):
    text=snapshot['text']['body']['content']
    loss=json.loads(snapshot['loss_report']['body']['content'])
    assert loss['params']['lang']=='chi_sim','English-only output cannot qualify Chinese OCR'
    positions=json.loads(snapshot['document_structure']['body']['content'])
    position=next(p for p in positions if '扫描中文页' in ''.join(text[p['char_start']:p['char_end']].split()))
    excerpt=text[position['char_start']:position['char_end']]
    locator={'type':'ocr_line','job_id':job,'attempt':snapshot['job']['body']['attempt'],'kind':position['kind'],'path':position['path'],'char_start':position['char_start'],'char_end':position['char_end'],'result_sha256':snapshot['document_structure']['body']['metadata']['sha256'],'loss_sha256':snapshot['loss_report']['body']['metadata']['sha256']}
    return {'revision':source['sha256'],'position':json.dumps(locator),'checksum':hashlib.sha256(excerpt.encode()).hexdigest()}


def ocr_page_body(source,job,snapshot):
    validate_outputs('png',snapshot,('扫描中文页二',))
    return location_body('png',source,job,snapshot,b'')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate',type=Path,required=True)
    parser.add_argument('--tessdata',type=Path,required=True)
    parser.add_argument('--tesseract',type=Path,required=True)
    args=parser.parse_args()
    base_raw=Path(base.__file__).read_bytes()
    assert hashlib.sha256(base_raw.replace(b'\r\n',b'\n')).hexdigest()==BASE_PREIMAGE,'Base probe changed; review and update the exact preimage before qualification'
    resources=validate_chinese_resources(args.tesseract,args.tessdata)
    env={'ARCHEAXIS_OCR_LANG':'chi_sim','ARCHEAXIS_OCR_TESSDATA':str(args.tessdata.resolve()),'TESSDATA_PREFIX':str(args.tessdata.resolve()),'TESSERACT_CMD':str(args.tesseract.resolve())}
    prior_env={key:os.environ.get(key) for key in env}
    overrides={'KINDS':KINDS,'MARKERS':MARKERS,'GENERATOR':GENERATOR,'validate_outputs':validate_outputs,'location_body':location_body,'ocr_page_body':ocr_page_body}
    prior_module={key:getattr(base,key) for key in overrides}
    prior_argv=sys.argv[:];captured=io.StringIO()
    try:
        os.environ.update(env)
        for key,value in overrides.items():setattr(base,key,value)
        sys.argv=[str(base.__file__),'--candidate',str(args.candidate)]
        with contextlib.redirect_stdout(captured):result=base.main()
    finally:
        sys.argv=prior_argv
        for key,value in prior_module.items():setattr(base,key,value)
        for key,value in prior_env.items():
            if value is None:os.environ.pop(key,None)
            else:os.environ[key]=value
    info=json.loads(captured.getvalue().splitlines()[-1]);old=Path(info['receipt'])
    receipt=json.loads(old.read_text(encoding='utf-8'))
    receipt['base_probe']={'lf_sha256':BASE_PREIMAGE,'raw_sha256':hashlib.sha256(base_raw).hexdigest(),'normalization':'CRLF to LF only','path':str(base.__file__)}
    receipt['ocr_resources']=resources
    receipt['limits']=['Selected actual Chinese phrases only; full recognition accuracy UNMEASURED','OCR canonical line/span location; bbox is actual review metadata','No installed UI, source package reconstruction or ASR','Independent new jobs preserve pinned historical attempts']
    try:
        assert validate_chinese_resources(args.tesseract,args.tessdata)==resources,'OCR resources changed during qualification'
    except Exception as error:
        receipt['ok']=False;receipt['resource_error']=f'{type(error).__name__}: {error}';result=1
    if receipt['ok']:
        receipt['qualification']='INTEGRATED_SELECTED_CHINESE_OCR_LOCATION_REPARSE_RESTART'
    output=old.with_name('common-chinese-ocr.json')
    output.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'ok':receipt['ok'],'receipt':str(output),'error':receipt.get('error')}))
    return result if not receipt['ok'] else 0
if __name__=='__main__':raise SystemExit(main())
