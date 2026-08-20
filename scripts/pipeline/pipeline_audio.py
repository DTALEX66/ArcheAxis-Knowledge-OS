# -*- coding: utf-8 -*-
"""pipeline_audio.py — 音频全量转写（F1）。

用法（在项目根）:
    env -u PYTHONPATH .venv/Scripts/python.exe scripts/pipeline/pipeline_audio.py

引擎：SenseVoice int8（快，~26x）→ faster-whisper 兜底。
输入：D:/All projects/ceshi 全部 mp3/m4a/wav/flac/mp4（mp4 先 ffmpeg 提音轨）。
输出：.hermes/task-runtime/audio_full_receipt.json
"""
import json, os, subprocess, sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ROOT = os.environ.get("ARCHEAXIS_PIPELINE_SOURCE_ROOT", "")
OUT = str(PROJECT_ROOT / ".hermes" / "task-runtime" / "audio_full_receipt.json")
WORK = str(PROJECT_ROOT / ".hermes" / "task-runtime" / "audio-work")
os.makedirs(WORK, exist_ok=True)

from app.ingestion.asr_adapter import transcribe_sense_voice, transcribe as transcribe_fw
from app.ingestion.content_cleaner import clean_text as strip_noise

def main() -> None:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--part', type=int, default=0)
    ap.add_argument('--parts', type=int, default=1)
    ap.add_argument('--audio-only', action='store_true', help='skip .mp4 (video tracks deferred)')
    args = ap.parse_args()
    if not ROOT:
        raise SystemExit("set ARCHEAXIS_PIPELINE_SOURCE_ROOT to an approved source directory")
    if args.audio_only:
        _AUDIO_EXTS = ('.mp3', '.m4a', '.wav', '.flac')
    else:
        _AUDIO_EXTS = ('.mp3', '.m4a', '.wav', '.flac', '.mp4')
    if args.parts > 1:
        import pathlib as _pl
        _out = _pl.Path(OUT)
        OUT_PART = str(_out.with_name(_out.stem + f".part{args.part}.json"))
    else:
        OUT_PART = OUT
    files = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        for f in filenames:
            if f.lower().endswith(_AUDIO_EXTS):
                p = os.path.join(dirpath, f)
                if os.path.getsize(p) > 0:
                    files.append(p)
    files = [p for i, p in enumerate(sorted(files)) if i % args.parts == args.part]
    print(f'audio files (part {args.part}/{args.parts}):', len(files), flush=True)
    receipts, ok, fail = [], 0, 0
    for idx, p in enumerate(files):
        rel = p.replace(ROOT + '/', '')
        t0 = __import__('time').monotonic()
        try:
            wav = os.path.join(WORK, f'a{idx}.wav')
            subprocess.run(['ffmpeg', '-y', '-i', p, '-vn', '-ac', '1', '-ar', '16000', wav],
                           capture_output=True, check=False)
            if not os.path.exists(wav) or os.path.getsize(wav) == 0:
                fail += 1; receipts.append({'file': rel, 'ok': False, 'error': 'ffmpeg failed'}); continue
            import subprocess as _sp
            import math as _math
            _pd = _sp.run(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1', wav],
                          capture_output=True, text=True)
            try: _dur = float((_pd.stdout or '0').strip() or 0)
            except ValueError: _dur = 0.0
            # chunked SenseVoice: <=8min segments bound memory (long-audio fix)
            parts = []
            seg = 480.0
            for _s in range(0, _math.ceil(max(_dur, 1) / seg)):
                _seg_wav = os.path.join(WORK, f's{idx}_{_s}.wav')
                _sp.run(['ffmpeg','-y','-ss',str(_s*seg),'-t',str(seg),'-i',wav,'-ac','1','-ar','16000',_seg_wav],
                        capture_output=True, check=False)
                if not os.path.exists(_seg_wav): continue
                _r = transcribe_sense_voice(_seg_wav)
                if _r:
                    parts.append(_r['text'])
                try: os.remove(_seg_wav)
                except OSError: pass
            if not parts:
                fail += 1; receipts.append({'file': rel, 'ok': False, 'error': 'sensevoice empty'}); continue
            text = strip_noise(''.join(parts))
            if not text.strip():
                fail += 1; receipts.append({'file': rel, 'ok': False, 'error': 'empty transcript'}); continue
            ok += 1
            receipts.append({'file': rel, 'ok': True, 'engine': 'sensevoice', 'chars': len(text),
                             'sec': round(__import__('time').monotonic() - t0, 1)})
            print(f'[{idx+1}/{len(files)}] ok {rel[:46]} ({len(text)}c)', flush=True)
        except Exception as e:
            fail += 1
            receipts.append({'file': rel, 'ok': False, 'error': repr(e)[:120]})
        try: os.remove(wav)
        except OSError: pass
    summary = {'total': len(files), 'ok': ok, 'fail': fail}
    with open(OUT_PART, 'w', encoding='utf-8') as f:
        json.dump({'summary': summary, 'receipts': receipts}, f, ensure_ascii=False)
    print('SUMMARY:', json.dumps(summary), flush=True)

if __name__ == '__main__':
    main()
