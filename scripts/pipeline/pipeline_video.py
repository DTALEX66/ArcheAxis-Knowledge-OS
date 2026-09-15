"""视频画面转化：全部 mp4 抽帧 + RapidOCR（画面文字知识提取，非音轨）。"""
import json
import os
import argparse
import subprocess
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ROOT = os.environ.get("ARCHEAXIS_PIPELINE_SOURCE_ROOT", "")
RUN_ROOT = Path(os.environ.get("ARCHEAXIS_RUN_ROOT", PROJECT_ROOT / ".project-local" / "task-runtime"))
ARTIFACT_ROOT = (RUN_ROOT / "artifacts" / "pipeline" / "video") if os.environ.get("ARCHEAXIS_RUN_ROOT") else (RUN_ROOT / "video")
OUT = str(ARTIFACT_ROOT / "video_ocr_receipt.json")
WORK = str(ARTIFACT_ROOT / "work")
os.makedirs(WORK, exist_ok=True)
Path(OUT).parent.mkdir(parents=True, exist_ok=True)
from app.ingestion.content_cleaner import clean_text as strip_noise
from app.ingestion.ocr_gate import assess as ocr_gate
from app.ingestion.rapid_ocr_adapter import convert_image_rapid
try:
    from source_preflight import validate_source  # noqa: E402
except ModuleNotFoundError:
    from scripts.pipeline.source_preflight import validate_source  # noqa: E402

if not ROOT:
    raise SystemExit("set ARCHEAXIS_PIPELINE_SOURCE_ROOT to an approved source directory")
try:
    ROOT = str(validate_source(Path(ROOT)))
except ValueError as exc:
    raise SystemExit(f"source root rejected: {exc}") from exc

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--max-files', type=int, default=0, help='process at most this many sorted inputs (0 = all)')
args = parser.parse_args()
if args.max_files < 0:
    raise SystemExit("--max-files must be non-negative")

videos = []
for dirpath, dirnames, filenames in os.walk(ROOT):
    for f in filenames:
        if f.lower().endswith('.mp4'):
            p = os.path.join(dirpath, f)
            if os.path.getsize(p) > 100 * 1024:
                videos.append(p)
print('videos:', len(videos), flush=True)
if args.max_files:
    videos = sorted(videos)[:args.max_files]

receipts = []
ok = fail = 0
for idx, p in enumerate(sorted(videos)):
    rel = str(Path(p).relative_to(Path(ROOT))).replace('\\', '/')
    t0 = time.monotonic()
    try:
        dur = subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1', p],
                            capture_output=True, text=True)
        dur = float((dur.stdout or '0').strip() or 0)
        n_frames = min(8, max(3, int(dur // 240) + 1))  # ~1 frame per 4 min, 3..8
        texts = []
        for i in range(n_frames):
            ts = (i + 0.5) / n_frames * dur
            frame = os.path.join(WORK, f'v{idx}_f{i}.png')
            subprocess.run(['ffmpeg','-y','-ss',str(ts),'-i',p,'-frames:v','1','-vf','scale=1280:-1',frame],
                           capture_output=True, check=False)
            if not os.path.exists(frame):
                continue
            r = convert_image_rapid(frame)
            if r['success'] and r.get('chars', 0) > 3:
                texts.append(f"[@{int(ts)}s] {r['text'].strip()}")
            try: os.remove(frame)
            except OSError: pass
        if not texts:
            fail += 1; receipts.append({'file': rel, 'ok': False, 'error': 'no readable frames'}); continue
        content = strip_noise('\n'.join(texts))
        gate = ocr_gate(content).verdict
        ok += 1
        receipts.append({'file': rel, 'ok': True, 'duration_s': round(dur, 1), 'frames': len(texts),
                         'chars': len(content), 'gate': gate, 'sec': round(time.monotonic()-t0, 1)})
        print(f'[{idx+1}/{len(videos)}] ok {rel[:44]} ({len(texts)}f {len(content)}c {gate})', flush=True)
    except Exception as e:
        fail += 1
        receipts.append({'file': rel, 'ok': False, 'error': repr(e)[:120]})

summary = {'total': len(videos), 'ok': ok, 'fail': fail, 'gates': {}}
with open(OUT, 'w', encoding='utf-8') as f:
    json.dump({'summary': summary, 'receipts': receipts}, f, ensure_ascii=False)
print('SUMMARY:', json.dumps(summary), flush=True)
