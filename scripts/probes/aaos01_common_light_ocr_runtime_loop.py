"""Actual candidate common light formats and OCR; authored sources, never fabricated OCR."""
from __future__ import annotations
import argparse
import base64
import hashlib
import json
import subprocess
import time
import uuid
from pathlib import Path
import aaos01_office_runtime_loop as office

REPO = Path(__file__).resolve().parents[2]
KINDS = {"md":"text", "csv":"text", "json":"text", "html":"html", "srt":"subtitles", "vtt":"subtitles", "canvas":"canvas", "png":"image", "jpeg":"image", "pdf":"pdf"}
MARKERS = {"md": ("中文标题", "正文甲", "子标题乙"), "csv": ("中文姓名", "复合中文", "第二行"), "json": ("中文主题", "第一项", "第二项"), "html": ("网页中文标题", "正文甲", "正文乙"), "srt": ("字幕中文甲", "字幕中文乙"), "vtt": ("字幕中文甲", "字幕中文乙"), "canvas": ("节点中文甲", "节点中文乙"), "png": ("OCR PAGE ONE 6371",), "jpeg": ("OCR PAGE ONE 6371",)}
GENERATOR = r'''
import json,sys
from pathlib import Path
import fitz
root=Path(sys.argv[1]);root.mkdir(parents=True,exist_ok=True)
values={
'md':'# 中文标题\n\n正文甲 [链接](https://example.invalid)\n\n## 子标题乙\n- 列表中文\n```text\n# 不应成为标题\n```\n',
'csv':'中文姓名,内容,数量\n甲,"复合中文,带逗号",42\n乙,"第二行\n多行中文",7\n',
'json':json.dumps({'主题':'中文主题','列表':[{'值':'第一项'},{'值':'第二项'}],'嵌套':{'数值':42}},ensure_ascii=False),
'html':'<!doctype html><html><head><title>网页中文标题</title></head><body><h1>网页中文标题</h1><p>正文甲</p><table><tr><td>正文乙</td><td>42</td></tr></table><script>FORBIDDEN_SCRIPT_TEXT</script></body></html>',
'srt':'1\n00:00:01,000 --> 00:00:03,000\n字幕中文甲\n多行证据\n\n2\n00:00:02,500 --> 00:00:04,500\n字幕中文乙\n',
'vtt':'WEBVTT\n\nNOTE omitted note\nFORBIDDEN_NOTE_TEXT\n\nfirst\n00:00:01.000 --> 00:00:03.000\n<b>字幕中文甲</b>\n多行证据\n\nsecond\n00:00:02.500 --> 00:00:04.500\n字幕中文乙\n',
'canvas':json.dumps({'nodes':[{'id':'a','type':'text','text':'节点中文甲','x':10,'y':20,'width':300,'height':100,'color':'2'},{'id':'b','type':'text','text':'节点中文乙','x':410,'y':20,'width':300,'height':100},{'id':'ref','type':'file','file':'unresolved-owned-reference.md','x':20,'y':200,'width':200,'height':80}], 'edges':[{'id':'e','fromNode':'a','toNode':'b','fromSide':'right','toSide':'left','label':'中文关系'}]},ensure_ascii=False)}
for ext,text in values.items(): (root/('complex.'+ext)).write_text(text,encoding='utf-8')
scan=fitz.open()
for i,english in enumerate(('OCR PAGE ONE 6371','OCR PAGE TWO 8429')):
 native=fitz.open();p=native.new_page(width=700,height=250)
 p.insert_text((30,70),english,fontsize=26)
 p.insert_text((30,135),'扫描中文页'+('一' if i==0 else '二'),fontname='china-s',fontsize=24)
 pix=p.get_pixmap(dpi=150);png=pix.tobytes('png')
 if i==0:
  (root/'complex.png').write_bytes(png)
  (root/'complex.jpeg').write_bytes(pix.tobytes('jpeg'))
 page=scan.new_page(width=700,height=250);page.insert_image(page.rect,stream=png)
 native.close()
(root/'complex.pdf').write_bytes(scan.tobytes());scan.close()
print(json.dumps({'materials':'SYNTHETIC_AUTHORED','PyMuPDF':fitz.VersionBind,'scan_pages':2,'ocr_languages_qualified':['eng'],'chinese_scan_recognition':'UNMEASURED'},ensure_ascii=False))
'''


def verify_artifacts(snapshot):
    assert snapshot['job']['body']['state'] == 'succeeded', snapshot['job']
    for key in ('text','document_structure','loss_report','quality'):
        assert snapshot[key]['status'] == 200, snapshot[key]
    for key in ('text','document_structure','loss_report'):
        out=snapshot[key]['body'];raw=out['content'].encode()
        assert out['metadata']['sha256']==hashlib.sha256(raw).hexdigest()
        assert out['metadata']['byte_length']==len(raw)


def validate_outputs(extension, snapshot, expected=None):
    verify_artifacts(snapshot)
    text=snapshot['text']['body']['content'];loss=json.loads(snapshot['loss_report']['body']['content'])
    assert loss.get('engine') and loss.get('engine_version') and loss.get('loss_note')
    assert isinstance(loss.get('losses'),list)
    compact=''.join(text.split())
    assert all(''.join(x.split()) in compact for x in (expected or MARKERS[extension])), text
    params=loss['params']
    if extension=='md':
        assert params['format']['heading_count']==2
    if extension=='csv':
        assert params['format']['row_count']==3 and params['format']['column_count']==3
        assert any(x['row']==3 and x['column']==2 and '\n' in x['value'] for x in params['format']['locations'])
    if extension=='json':
        assert any(x['value']=='第二项' for x in params['format']['locations'])
    if extension=='html': assert 'FORBIDDEN_SCRIPT_TEXT' not in text
    if extension=='vtt':
        assert 'FORBIDDEN_NOTE_TEXT' not in text and '<b>' not in text
        assert 'NOTE' in loss['loss_note']
    if extension=='canvas':
        extra=params['worker_output']
        assert len(extra['node_geometry'])==3 and len(extra['edges'])==1 and extra['references']
        assert 'group containment' in loss['loss_note']
    if extension in ('png','jpeg'):
        assert params['regions'] and all(x['bbox']['w']>0 and x['bbox']['h']>0 for x in params['regions'])
        assert params['input_transport']=='stdin'
    return text,loss


def location_body(extension, source, job, snapshot, raw):
    text,loss=validate_outputs(extension,snapshot)
    common={'job_id':job,'attempt':snapshot['job']['body']['attempt']}
    if extension in ('csv','json'):
        p=next(p for p in loss['params']['format']['locations'] if isinstance(p.get('value'),str) and ('中文' in p['value'] or p['value']=='第二项'))
        locator={'type':'format_location',**common,'kind':p['kind'],'path':p['path']};excerpt=p['value']
    elif extension=='md':
        excerpt='正文甲';needle=excerpt.encode();start=raw.index(needle)
        locator={'type':'text','start':start,'end':start+len(needle)}
    elif extension in ('png','jpeg'):
        p=next(p for p in json.loads(snapshot['document_structure']['body']['content']) if '6371' in text[p['char_start']:p['char_end']] or '8429' in text[p['char_start']:p['char_end']])
        excerpt=text[p['char_start']:p['char_end']]
        locator={'type':'ocr_line',**common,'kind':p['kind'],'path':p['path'],'char_start':p['char_start'],'char_end':p['char_end'],'result_sha256':snapshot['document_structure']['body']['metadata']['sha256'],'loss_sha256':snapshot['loss_report']['body']['metadata']['sha256']}
    else:
        p=next(p for p in loss['params']['worker_structure'] if text[p['char_start']:p['char_end']].strip())
        excerpt=text[p['char_start']:p['char_end']]
        locator={'type':'worker_structure',**common,'kind':p['kind'],'path':p['path']}
    return {'revision':source['sha256'],'position':json.dumps(locator),'checksum':hashlib.sha256(excerpt.encode()).hexdigest()}


def located(call,source,body):
    path=f"/api/v1/sources/{source['source_id']}/anchors"
    anchor=call('POST',path,body,201)
    assert anchor['location_status']=='located'
    call('POST',path,{**body,'checksum':'0'*64},400)
    resolution=call('GET',path+f"/{anchor['anchor_id']}/resolve")
    assert resolution['status']=='CURRENT' and resolution['scope']=='locator_provenance_only',resolution
    return {'source':source,'anchor':anchor,'resolution':resolution}


def execute(call,client,base,token,job):
    call('POST',f'/api/v1/jobs/{job}/executions',{'deadline_ms':60000},202,headers={'idempotency-key':job})
    deadline=time.monotonic()+65
    while call('GET',f'/api/v1/jobs/{job}')['state'] not in ('succeeded','failed','cancelled','rejected'):
        assert time.monotonic()<deadline,'actual worker deadline expired'
        time.sleep(.1)
    return office.capture(client,base,token,job)


def run_job(call,client,base,token,source,extension,raw):
    job='light-'+uuid.uuid4().hex
    call('POST','/api/v1/jobs',{'job_id':job,'kind':KINDS[extension],'input_ref':source['source_id']},202)
    snap=execute(call,client,base,token,job)
    record={'job_id':job,'snapshot':snap,'locations':[],'pages':[]}
    if extension!='pdf':
        validate_outputs(extension,snap)
        record['locations'].append(located(call,source,location_body(extension,source,job,snap,raw)))
        return record
    verify_artifacts(snap)
    loss=json.loads(snap['loss_report']['body']['content'])
    assert loss['params']['pages_without_text']==[1,2] and not snap['text']['body']['content'].strip()
    pages=call('GET',f"/api/v1/sources/{source['source_id']}/pages")
    assert pages['page_count']==2
    for page in pages['pages']:
        assert page['job_id'] and page['page'] in (1,2)
        original=call('GET',f"/api/v1/sources/{page['source_id']}/original")
        page_raw=base64.b64decode(original['content_base64']);assert hashlib.sha256(page_raw).hexdigest()==page['sha256']
        page_job=f"{job}-page-{page['page']}"
        state=call('GET',f'/api/v1/jobs/{page_job}')
        assert state['input_ref']==page['source_id'], 'new PDF attempt page job must match actual page source'
        page_snap=office.capture(client,base,token,page_job) if state['state']=='succeeded' else execute(call,client,base,token,page_job)
        expected='OCR PAGE ONE 6371' if page['page']==1 else 'OCR PAGE TWO 8429'
        validate_outputs('png',page_snap,(expected,))
        page_source={'source_id':page['source_id'],'sha256':page['sha256']}
        # location_body requires format markers; page two carries its own real OCR marker.
        page_body=location_body('png',page_source,page_job,page_snap,page_raw) if page['page']==1 else ocr_page_body(page_source,page_job,page_snap)
        record['locations'].append(located(call,page_source,page_body))
        record['pages'].append({'page':page['page'],'source':page_source,'original':original,'job_id':page_job,'snapshot':page_snap})
    record['page_relation']=call('GET',f"/api/v1/sources/{source['source_id']}/pages")
    assert record['page_relation']['recognised_count']==2
    return record


def ocr_page_body(source,job,snapshot):
    text,loss=validate_outputs('png',snapshot,('OCR PAGE TWO 8429',))
    p=next(p for p in json.loads(snapshot['document_structure']['body']['content']) if '8429' in text[p['char_start']:p['char_end']])
    locator={'type':'ocr_line','job_id':job,'attempt':snapshot['job']['body']['attempt'],'kind':p['kind'],'path':p['path'],'char_start':p['char_start'],'char_end':p['char_end'],'result_sha256':snapshot['document_structure']['body']['metadata']['sha256'],'loss_sha256':snapshot['loss_report']['body']['metadata']['sha256']}
    return {'revision':source['sha256'],'position':json.dumps(locator),'checksum':hashlib.sha256(text[p['char_start']:p['char_end']].encode()).hexdigest()}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--candidate',type=Path,required=True);args=parser.parse_args();candidate=args.candidate.resolve()
    dev=office.load('light_ocr_dev',REPO/'scripts/runtime/dev.py');paths=dev.layout(REPO);dev.prepare(paths);work=paths['run']
    launcher=office.load('light_ocr_launcher',REPO/'scripts/release/backend_launcher.py');client=office.load('light_ocr_client',REPO/'shared/core_client.py')
    receipt={'ok':False,'qualification':'NOT_EXECUTED','materials':'SYNTHETIC_AUTHORED','execution':'ACTUAL_CANDIDATE_CORE_WORKERS','formats':[],'limits':['English OCR sentinel content only; Chinese scan recognition UNMEASURED','MD anchor binds immutable original UTF-8 byte span; derived structure separately checked','No installed UI or source-application navigation','No format reconstruction or ASR','Independent reparse new job does not supersede historical pinned attempts']};child=None
    try:
        profile=launcher.load_profile(candidate)
        dirty,patch=dev.worktree_identity(REPO);receipt['source']={'commit':dev.git(REPO,'rev-parse','HEAD'),'dirty':dirty,'patch_sha256':patch,'changes':office.source_changes(dev)}
        receipt['candidate']={name:office.identity(candidate/name) for name in ('core/archeaxis-api.exe','worker-profile.json','backend-runtime-manifest.json')}
        material=work/'materials';generated=subprocess.run([str(profile['python']),'-B','-I','-c',GENERATOR,str(material)],capture_output=True,text=True,encoding='utf-8',timeout=60)
        receipt['generator']={'exit':generated.returncode,'stdout':generated.stdout,'stderr':generated.stderr};assert generated.returncode==0,'actual candidate generator failed'
        child,base,token,_=office.start(candidate,work,launcher)
        def call(method,path,body=None,expected=200,headers=None):
            status,result=client.call(base,method,path,token,body,extra_headers=headers)
            assert status==expected,{'path':path,'status':status,'result':result}
            return result
        for extension in KINDS:
            raw=(material/f'complex.{extension}').read_bytes();source=call('POST','/api/v1/imports',client.import_request(f'complex.{extension}',raw),202)
            assert source['sha256']==hashlib.sha256(raw).hexdigest();path=f"/api/v1/sources/{source['source_id']}/original";original=call('GET',path)
            assert base64.b64decode(original['content_base64'])==raw
            record={'extension':extension,'source':source,'original':original,'input':office.identity(material/f'complex.{extension}')};receipt['formats'].append(record)
            record['first']=run_job(call,client,base,token,source,extension,raw)
            history={item['source']['source_id']:call('GET',f"/api/v1/sources/{item['source']['source_id']}/anchors") for item in record['first']['locations']}
            record['reparse']=run_job(call,client,base,token,source,extension,raw)
            assert record['first']['job_id']!=record['reparse']['job_id']
            for key in ('text','document_structure'): assert record['first']['snapshot'][key]==record['reparse']['snapshot'][key]
            assert call('GET',path)==original
            for sid,before in history.items():
                after=call('GET',f'/api/v1/sources/{sid}/anchors');assert all(row in after['anchors'] for row in before['anchors'])
            if extension=='pdf':
                for first,second in zip(record['first']['pages'],record['reparse']['pages'],strict=True):
                    assert first['source']==second['source'] and first['original']==second['original']
                    assert first['job_id']!=second['job_id']
                    assert first['snapshot']['text']==second['snapshot']['text']
            record['anchors']={item['source']['source_id']:call('GET',f"/api/v1/sources/{item['source']['source_id']}/anchors") for item in record['reparse']['locations']}
            for phase in ('first','reparse'):
                for item in record[phase]['locations']:
                    s=item['source'];ap=f"/api/v1/sources/{s['source_id']}/anchors/{item['anchor']['anchor_id']}/resolve"
                    assert call('GET',ap)==item['resolution'],'reparse changed historical locator'
        launcher.stop(child);child=None;child,base,token,_=office.start(candidate,work,launcher)
        for record in receipt['formats']:
            source=record['source'];assert call('GET',f"/api/v1/sources/{source['source_id']}/original")==record['original']
            for sid,anchors in record['anchors'].items(): assert call('GET',f'/api/v1/sources/{sid}/anchors')==anchors
            if record['extension']=='pdf': assert call('GET',f"/api/v1/sources/{source['source_id']}/pages")==record['reparse']['page_relation']
            for phase in ('first','reparse'):
                run=record[phase];assert office.capture(client,base,token,run['job_id'])==run['snapshot']
                for page in run['pages']:
                    assert call('GET',f"/api/v1/sources/{page['source']['source_id']}/original")==page['original']
                    assert office.capture(client,base,token,page['job_id'])==page['snapshot']
                for item in run['locations']:
                    s=item['source'];assert call('GET',f"/api/v1/sources/{s['source_id']}/anchors/{item['anchor']['anchor_id']}/resolve")==item['resolution']
            record['restart_equal']=True
        receipt['ok']=True;receipt['qualification']='INTEGRATED_SELECTED_LIGHT_CONTENT_OCR_LOCATION_REPARSE_RESTART'
    except Exception as error: receipt['error']=f'{type(error).__name__}: {error}'
    finally:
        if child is not None:
            try: launcher.stop(child)
            except Exception as error: receipt['ok']=False;receipt['cleanup_error']=f'{type(error).__name__}: {error}'
        receipt['source_consistent']=dev.worktree_identity(REPO)==(dirty,patch) if 'source' in receipt else False
        if not receipt['source_consistent']: receipt['ok']=False
        output=paths['artifacts']/'common-light-ocr.json';output.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({'ok':receipt['ok'],'receipt':str(output),'error':receipt.get('error')}))
    return 0 if receipt['ok'] else 1
if __name__=='__main__': raise SystemExit(main())
