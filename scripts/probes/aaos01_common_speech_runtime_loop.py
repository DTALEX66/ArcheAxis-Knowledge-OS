"""Actual candidate WAV/MP3/MP4 audio-content qualification; local authored speech only.

MP4 qualification covers the audio transcript and approximate decoded artifacts,
not visual understanding. Visual inference is disabled for this process.
"""
from __future__ import annotations
import argparse
import base64
import hashlib
import json
import os
import subprocess
import time
import uuid
import unicodedata
from pathlib import Path
import aaos01_office_runtime_loop as office
import aaos01_common_light_ocr_runtime_loop as light
REPO=Path(__file__).resolve().parents[2]
SPEECH='This is a recorded speech sample. The blue circle contains seven notes. Keep the original source. The blue circle contains seven notes.'
EXPECTED=('blue circle','seven notes','original source')
SAPI_SCRIPT=r'''
param([string]$Output,[string]$Text)
$ErrorActionPreference='Stop'
[Console]::OutputEncoding=New-Object System.Text.UTF8Encoding($false)
$voice=New-Object -ComObject SAPI.SpVoice
$voices=$voice.GetVoices('Language=409')
if ($voices.Count -lt 1) { throw 'Required offline English SAPI voice is missing' }
$voice.Voice=$voices.Item(0)
$stream=New-Object -ComObject SAPI.SpFileStream
$stream.Format.Type=18
$stream.Open($Output,3,$false)
try {
 $voice.AudioOutputStream=$stream
 $voice.Rate=-1
 $null=$voice.Speak($Text,0)
} finally { $stream.Close() }
@{engine='Windows offline SAPI';voice=$voice.Voice.GetDescription();language='en-US';text=$Text} | ConvertTo-Json -Compress
'''


NORMALIZATION = "Unicode NFKC + casefold; retain Unicode letters/numbers, remove whitespace/punctuation; selected phrases only, never full transcription accuracy"


def normalize_phrase(text):
    return "".join(char for char in unicodedata.normalize("NFKC", text).casefold() if char.isalnum())


def selected_phrases(reference, expected=None, owner_input=False):
    if owner_input:
        assert expected, "Selected spoken input requires at least one explicit --expected-phrase"
    phrases = tuple(expected) if expected is not None else EXPECTED
    assert phrases and all(isinstance(phrase,str) and normalize_phrase(phrase) for phrase in phrases), "Expected phrases must contain Unicode letters/numbers"
    normalized = normalize_phrase(reference)
    assert all(normalize_phrase(phrase) in normalized for phrase in phrases), "Selected expected phrase is absent from the supplied transcript"
    return phrases


def validate_language(language):
    language = language.strip().lower()
    if language != "auto":
        from faster_whisper.tokenizer import _LANGUAGE_CODES
        assert language in _LANGUAGE_CODES, "Language is not supported by the existing faster-whisper contract"
    return language


def identity(path):
    path=Path(path);digest=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):digest.update(block)
    return {'path':str(path),'bytes':path.stat().st_size,'sha256':digest.hexdigest()}


def declared_model(model):
    prepared=office.load('speech_prepared_assets',REPO/'scripts/ci/prepare_common_asr.py')
    selected=prepared.lexical_path(model)
    if selected.is_relative_to(REPO/'.project-local'):
        return prepared.validate_prepared_model(selected,REPO)
    registry=json.loads((REPO/'config/environment/external-resources-index.json').read_text(encoding='utf-8'))
    def find(value):
        if isinstance(value,dict):
            if value.get('resource_id')=='ext.models.faster-whisper-large-v3-turbo':return value
            for child in value.values():
                result=find(child)
                if result:return result
        elif isinstance(value,list):
            for child in value:
                result=find(child)
                if result:return result
        return None
    entry=find(registry);assert entry and entry.get('resolved_absolute'),'declared ASR resource identity missing'
    expected=Path(entry['resolved_absolute']).resolve()
    model=Path(model).resolve();assert model==expected,'model must be the exact project-declared local ASR resource'
    assert model.drive.casefold() not in ('e:','f:') and not str(model).startswith('\\\\')
    members={}
    for name in ('model.bin','config.json','tokenizer.json','preprocessor_config.json','vocabulary.json'):
        file=model/name;assert file.is_file() and file.stat().st_size>0,f'declared model component missing: {name}'
        assert not file.is_symlink() and not getattr(file.lstat(),'st_file_attributes',0)&0x400,'linked model component refused'
        members[name]=identity(file)
    return {'resource_id':entry['resource_id'],'local_only':True,'members':members}


def generate_speech(directory,powershell,ffmpeg,spoken_wav=None,transcript=None,expected=None):
    directory.mkdir(parents=True,exist_ok=True)
    if spoken_wav is not None:
        source=Path(spoken_wav).resolve();truth=Path(transcript).resolve()
        assert source.is_relative_to(REPO) and truth.is_relative_to(REPO), 'Speech input must be explicitly selected inside this project'
        assert source.suffix.lower()=='.wav' and truth.suffix.lower()=='.txt' and source.is_file() and truth.is_file()
        reference=truth.read_text(encoding='utf-8-sig');phrases=selected_phrases(reference,expected,owner_input=True)
        (directory/'speech.wav').write_bytes(source.read_bytes());(directory/'speech.txt').write_bytes(truth.read_bytes())
        voice={'engine':'Explicit project-owned spoken input','text':reference,'source':identity(source),'truth':identity(truth),'human_truth_accuracy':'UNMEASURED'}
    else:
        phrases=selected_phrases(SPEECH,expected)
        script=directory/'generate-offline-speech.ps1';script.write_text(SAPI_SCRIPT,encoding='utf-8-sig')
        (directory/'speech.txt').write_text(SPEECH,encoding='utf-8')
        generated=subprocess.run([str(powershell),'-NoProfile','-NonInteractive','-File',str(script),'-Output',str(directory/'speech.wav'),'-Text',SPEECH],capture_output=True,timeout=90)
        stderr=generated.stderr.decode('mbcs' if os.name=='nt' else 'utf-8',errors='replace')
        assert generated.returncode==0,'Offline SAPI speech generation failed: '+json.dumps(stderr[:600],ensure_ascii=True)
        voice=json.loads(generated.stdout.decode('utf-8-sig').strip())
        assert voice['engine']=='Windows offline SAPI' and voice['text']==SPEECH
    commands=(['-i',str(directory/'speech.wav'),'-codec:a','libmp3lame','-q:a','2',str(directory/'speech.mp3')],
              ['-f','lavfi','-i','color=c=blue:s=320x180:r=5','-i',str(directory/'speech.wav'),'-c:v','mpeg4','-c:a','aac','-shortest',str(directory/'speech.mp4')])
    for args in commands:
        result=subprocess.run([str(ffmpeg),'-nostdin','-hide_banner','-loglevel','error','-y',*args],capture_output=True,text=True,timeout=90)
        assert result.returncode==0,'Actual speech container conversion failed: '+result.stderr[:300]
    return {'voice':voice,'expected_phrases':phrases,'normalization':NORMALIZATION,'transcript':identity(directory/'speech.txt'),'files':{ext:identity(directory/f'speech.{ext}') for ext in ('wav','mp3','mp4')}}


def validate_asr(extension,snapshot,expected=EXPECTED):
    light.verify_artifacts(snapshot)
    text=snapshot['text']['body']['content'];loss=json.loads(snapshot['loss_report']['body']['content'])
    normalized=normalize_phrase(text)
    assert expected and all(normalize_phrase(marker) and normalize_phrase(marker) in normalized for marker in expected),'Actual expected speech content missing: '+text
    output=loss['params']['worker_output']
    assert output['cues'] and output['raw_cues'] and output['alignment_status']=='complete'
    assert not output.get('alignment_issues')
    duration=output['duration_ms'];assert duration>0
    for cue in output['cues']:
        assert 0<=cue['start_ms']<cue['end_ms']<=duration and cue['text'].strip()
    if extension=='mp4':
        assert loss['engine']=='python-worker-video'
        assert output['stages']['asr']['state']=='succeeded'
        assert output['pipeline_state']=='partial' and output['stages']['visual']['state']=='failed'
        assert output['stages']['visual']['reason']=='invalid_local_visual_configuration'
        assert output['visual_results']==[],'No visual inference is authorized in this qualification'
        assert output['frames'] and output['audio_wav']
        assert loss['params']['sampling']['continuous_coverage'] is False
        assert loss['params']['sampling']['actual_pts_available'] is False
        assert loss['params']['asr']['params']['model']=='faster-whisper-large-v3-turbo'
    else:
        assert loss['engine']=='python-worker-transcribe' and output['processing_status']=='complete'
        assert loss['params']['model']=='faster-whisper-large-v3-turbo'
    return output


def time_location(call,source,job,snapshot,expected=EXPECTED):
    output=json.loads(snapshot['loss_report']['body']['content'])['params']['worker_output']
    matches=[(i,phrase) for i,cue in enumerate(output['cues']) for phrase in expected if normalize_phrase(phrase) and normalize_phrase(phrase) in normalize_phrase(cue['text'])]
    assert matches,'Selected phrase has no single actually located cue'
    index,phrase=matches[0];cue=output['cues'][index]
    locator={'type':'time','job_id':job,'attempt':snapshot['job']['body']['attempt'],'cue_index':index,'start_ms':cue['start_ms'],'end_ms':cue['end_ms'],'result_sha256':snapshot['loss_report']['body']['metadata']['sha256']}
    body={'revision':source['sha256'],'checksum':hashlib.sha256(cue['text'].encode()).hexdigest(),'position':json.dumps(locator)}
    result=light.located(call,source,body);result['matched_phrase']=phrase;result['normalization']=NORMALIZATION
    return result


def run_job(call,client,base,token,source,extension,expected=EXPECTED):
    job='speech-'+uuid.uuid4().hex
    call('POST','/api/v1/jobs',{'job_id':job,'kind':'video' if extension=='mp4' else 'transcribe','input_ref':source['source_id']},202)
    call('POST',f'/api/v1/jobs/{job}/executions',{'deadline_ms':300000},202,headers={'idempotency-key':job})
    deadline=time.monotonic()+310
    while call('GET',f'/api/v1/jobs/{job}')['state'] not in ('succeeded','failed','cancelled','rejected'):
        assert time.monotonic()<deadline,'actual ASR job deadline exceeded';time.sleep(.2)
    snap=office.capture(client,base,token,job);validate_asr(extension,snap,expected)
    return {'job_id':job,'snapshot':snap,'location':time_location(call,source,job,snap,expected)}


def projection(snapshot):
    # Decoder transfer filenames vary between independent jobs; compare content and
    # actual cues rather than claiming the whole runtime receipt is identical.
    output=json.loads(snapshot['loss_report']['body']['content'])['params']['worker_output']
    return {'text':snapshot['text'],'structure':snapshot['document_structure'],'cues':output['cues'],'raw_cues':output['raw_cues'],'duration_ms':output['duration_ms']}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--candidate',type=Path,required=True);parser.add_argument('--expected-phrase',action='append');parser.add_argument('--language',default='auto');parser.add_argument('--speech-wav',type=Path);parser.add_argument('--speech-transcript',type=Path);parser.add_argument('--model-dir',type=Path,required=True);parser.add_argument('--ffmpeg',type=Path,required=True);parser.add_argument('--powershell',type=Path);args=parser.parse_args()
    candidate=args.candidate.resolve();dev=office.load('speech_dev',REPO/'scripts/runtime/dev.py');paths=dev.layout(REPO);dev.prepare(paths);work=paths['run'];launcher=office.load('speech_launcher',REPO/'scripts/release/backend_launcher.py');client=office.load('speech_client',REPO/'shared/core_client.py')
    receipt={'ok':False,'qualification':'NOT_EXECUTED','materials':'SYNTHETIC_AUTHORED_OFFLINE_SPOKEN_SPEECH','execution':'ACTUAL_CANDIDATE_CORE_ASR','formats':[],'limits':['Only explicitly selected normalized phrases qualified; full transcript and recognition accuracy UNMEASURED','No visual model inference; MP4 audio content qualified independently, multimedia pipeline PARTIAL','Approximate sampled seek frames do not establish continuous visual coverage','No installed UI/source format reconstruction']};child=None
    original_environment={key:os.environ.get(key) for key in ('ARCHEAXIS_ASR_MODEL_DIR','ARCHEAXIS_ASR_LANG','ARCHEAXIS_ASR_DEVICE','ARCHEAXIS_CAPTION_PROTOCOL','HF_HUB_OFFLINE','TRANSFORMERS_OFFLINE','FFMPEG_CMD')}
    try:
        receipt['model']=declared_model(args.model_dir);profile=launcher.load_profile(candidate)
        tool_paths=office.load('speech_tool_paths',REPO/'services/python-workers/tool_paths.py')
        declared_ffmpeg=tool_paths.declared_location('ffmpeg')
        assert declared_ffmpeg,'Project-declared ffmpeg is unavailable'
        assert args.ffmpeg.resolve()==Path(declared_ffmpeg).resolve(),'ffmpeg must match project declaration'
        receipt['ffmpeg']=identity(args.ffmpeg)
        assert (args.speech_wav is None)==(args.speech_transcript is None),'Spoken WAV and transcript must be selected together'
        if args.speech_wav is None and args.powershell is None:
            system_root=os.environ.get('SystemRoot')
            assert system_root,'SystemRoot is required for offline Windows speech generation'
            args.powershell=Path(system_root)/'System32/WindowsPowerShell/v1.0/powershell.exe'
        receipt['material']=generate_speech(work/'materials',args.powershell,args.ffmpeg,args.speech_wav,args.speech_transcript,args.expected_phrase)
        phrases=tuple(receipt['material']['expected_phrases']);language=validate_language(args.language)
        receipt['selected_content']={'expected_phrases':phrases,'language':language,'normalization':NORMALIZATION,'recognition_accuracy':'UNMEASURED'}
        if args.speech_wav is not None: receipt['materials']='EXPLICIT_PROJECT_SPOKEN_INPUT'
        dirty,patch=dev.worktree_identity(REPO);receipt['source']={'commit':dev.git(REPO,'rev-parse','HEAD'),'dirty':dirty,'patch_sha256':patch,'changes':office.source_changes(dev)}
        receipt['candidate']={name:office.identity(candidate/name) for name in ('core/archeaxis-api.exe','worker-profile.json','backend-runtime-manifest.json')}
        receipt['interpreter']=office.identity(profile['python'])
        os.environ.update({'ARCHEAXIS_ASR_MODEL_DIR':str(args.model_dir.resolve()),'ARCHEAXIS_ASR_LANG':language,'ARCHEAXIS_ASR_DEVICE':'cpu','ARCHEAXIS_CAPTION_PROTOCOL':'disabled-for-audio-qualification','HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1','FFMPEG_CMD':str(args.ffmpeg.resolve())})
        child,base,token,_=office.start(candidate,work,launcher)
        def call(method,path,body=None,expected=200,headers=None):
            status,result=client.call(base,method,path,token,body,extra_headers=headers);assert status==expected,{'path':path,'status':status,'result':result};return result
        for extension in ('wav','mp3','mp4'):
            raw=(work/'materials'/f'speech.{extension}').read_bytes();source=call('POST','/api/v1/imports',client.import_request(f'speech.{extension}',raw),202)
            assert source['sha256']==hashlib.sha256(raw).hexdigest();path=f"/api/v1/sources/{source['source_id']}/original";original=call('GET',path);assert base64.b64decode(original['content_base64'])==raw
            record={'extension':extension,'source':source,'original':original};receipt['formats'].append(record)
            record['first']=run_job(call,client,base,token,source,extension,phrases);anchor_path=f"/api/v1/sources/{source['source_id']}/anchors";before=call('GET',anchor_path)
            record['reparse']=run_job(call,client,base,token,source,extension,phrases);assert record['first']['job_id']!=record['reparse']['job_id'] and projection(record['first']['snapshot'])==projection(record['reparse']['snapshot'])
            record['anchors']=call('GET',anchor_path);assert all(row in record['anchors']['anchors'] for row in before['anchors']);assert call('GET',path)==original
        launcher.stop(child);child=None;child,base,token,_=office.start(candidate,work,launcher)
        for record in receipt['formats']:
            sid=record['source']['source_id'];assert call('GET',f'/api/v1/sources/{sid}/original')==record['original'];assert call('GET',f'/api/v1/sources/{sid}/anchors')==record['anchors']
            for phase in ('first','reparse'):
                run=record[phase];assert office.capture(client,base,token,run['job_id'])==run['snapshot'];item=run['location'];assert call('GET',f"/api/v1/sources/{sid}/anchors/{item['anchor']['anchor_id']}/resolve")==item['resolution']
            record['restart_equal']=True
        receipt['model_after']=declared_model(args.model_dir);assert receipt['model']==receipt['model_after'],'shared model changed during qualification'
        receipt['ok']=True;receipt['qualification']='INTEGRATED_SELECTED_PHRASE_AUDIO_CONTENT_TIME_REPARSE_RESTART'
    except Exception as error:receipt['error']=f'{type(error).__name__}: {error}'
    finally:
        if child is not None:
            try:launcher.stop(child)
            except Exception as error:receipt['ok']=False;receipt['cleanup_error']=f'{type(error).__name__}: {error}'
        for key,value in original_environment.items():
            if value is None:os.environ.pop(key,None)
            else:os.environ[key]=value
        receipt['source_consistent']=dev.worktree_identity(REPO)==(dirty,patch) if 'source' in receipt else False
        if not receipt['source_consistent']: receipt['ok']=False
        output=paths['artifacts']/'common-speech.json';output.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({'ok':receipt['ok'],'receipt':str(output),'error':receipt.get('error')}))
    return 0 if receipt['ok'] else 1
if __name__=='__main__':raise SystemExit(main())
