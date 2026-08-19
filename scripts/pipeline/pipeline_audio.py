# -*- coding: utf-8 -*-
"""pipeline_audio.py — 音频全量转写（F1）。

用法（在项目根）:
    env -u PYTHONPATH .venv\Scripts\python.exe scripts/pipeline/pipeline_audio.py

引擎：SenseVoice int8（快，~26x）→ faster-whisper 兜底。
输入：D:/All projects/ceshi 全部 mp3/m4a/wav/flac/mp4（mp4 先 ffmpeg 提音轨）。
输出：.hermes/task-runtime/audio_full_receipt.json
"""
import json, os, subprocess, sys
sys.stdout.reconfigure(encoding='utf-8')

ROOT = r"D:/All projects/ceshi"
OUT = r"D:/All projects/ArcheAxis-Knowledge-OS/.hermes/task-runtime/audio_full_receipt.json"
WORK = r"D:/All projects/ArcheAxis-Knowledge-OS/.hermes/task-runtime/audio-work"
os.makedirs(WORK, exist_ok=True)

from app.ingestion.asr_adapter import transcribe_sense_voice, transcribe as transcribe_fw
from app.ingestion.content_cleaner import clean_text as strip_noise

def main() -> None:
    files = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        for f in filenames:
            if f.lower().endswith(('.mp3', '.m4a', '.wav', '.flac', '.mp4')):
                p = os.path.join(dirpath, f)
                if os.path.getsize(p) > 0:
                    files.append(p)
    print('audio files:', len(files), flush=True)
    receipts, ok, fail = [], 0, 0
    for idx, p in enumerate(sorted(files)):
        rel = p.replace(ROOT + '/', '')
        t0 = __import__('time').monotonic()
        try:
            wav = os.path.join(WORK, f'a{idx}.wav')
            subprocess.run(['ffmpeg', '-y', '-i', p, '-vn', '-ac', '1', '-ar', '16000', wav],
                           capture_output=True, check=False)
            if not os.path.exists(wav) or os.path.getsize(wav) == 0:
                fail += 1; receipts.append({'file': rel, 'ok': False, 'error': 'ffmpeg failed'}); continue
            r = transcribe_sense_voice(wav) or transcribe_fw(wav)
            text = strip_noise(r['text'])
            if not text.strip():
                fail += 1; receipts.append({'file': rel, 'ok': False, 'error': 'empty transcript'}); continue
            ok += 1
            receipts.append({'file': rel, 'ok': True, 'engine': r.get('engine', 'asr'), 'chars': len(text),
                             'sec': round(__import__('time').monotonic() - t0, 1)})
            print(f'[{idx+1}/{len(files)}] ok {rel[:46]} ({len(text)}c)', flush=True)
        except Exception as e:
            fail += 1
            receipts.append({'file': rel, 'ok': False, 'error': repr(e)[:120]})
        try: os.remove(wav)
        except OSError: pass
    summary = {'total': len(files), 'ok': ok, 'fail': fail}
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump({'summary': summary, 'receipts': receipts}, f, ensure_ascii=False)
    print('SUMMARY:', json.dumps(summary), flush=True)

if __name__ == '__main__':
    main()
