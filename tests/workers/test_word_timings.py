"""F10: word-level timings are asked for, carried, honoured, and offset like everything else.

The chain is HTTP body -> Core request identity -> worker parameters -> faster-whisper -> cues, and
a windowed transcription has to move word times the same way it moves cue times. Every case here
runs without a model: a fake model object stands in for faster-whisper so the wiring is checked,
while the declared receipt fields keep the difference between "requested" and "produced" visible.
"""

import importlib.util
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TRANSPORT = ROOT / "services/python-workers/transport/text_ndjson.py"
WORKER = ROOT / "services/python-workers/media/worker_transcribe.py"
WINDOW = ROOT / "services/python-workers/media/window_transcribe.py"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class _Word:
    def __init__(self, start, end, word):
        self.start, self.end, self.word = start, end, word


class _Segment:
    def __init__(self, start, end, text, words):
        self.start, self.end, self.text, self.words = start, end, text, words


class _Info:
    language = "en"
    language_probability = 0.93
    duration = 4.0


class _Model:
    """Stands in for faster-whisper and records what the caller asked the engine for."""

    def __init__(self):
        self.seen = None

    def transcribe(self, path, language=None, vad_filter=False, word_timestamps=False):
        self.seen = {"language": language, "vad_filter": vad_filter, "word_timestamps": word_timestamps}
        segments = [_Segment(0.0, 2.0, " hello there ",
                             [_Word(0.05, 0.5, "hello"), _Word(1.2, 2.0, "there")]),
                    _Segment(2.0, 3.5, "second cue", [_Word(2.1, 3.4, "second")])]
        return iter(segments), _Info()


class WordTimingsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("ARCHEAXIS_RUN_ROOT", str(ROOT / ".project-local/task-runtime"))
        cls.transport = _load("text_ndjson_words", TRANSPORT)
        cls.worker = _load("worker_transcribe_words", WORKER)
        cls.window = _load("window_transcribe_words", WINDOW)

    def test_words_is_accepted_for_transcribe_and_needs_no_split(self):
        plan = self.transport.declared_split("media.transcribe", {"words": True})
        self.assertIsNone(plan, "a word-timing request without a split is valid and has no plan")

    def test_an_unnamed_parameter_or_a_false_flag_is_refused(self):
        with self.assertRaises(self.transport.Rejected):
            self.transport.declared_split("media.transcribe", {"words": False})
        with self.assertRaises(self.transport.Rejected):
            self.transport.declared_split("media.transcribe", {"words": True, "speed": 2})
        with self.assertRaises(self.transport.Rejected):
            self.transport.declared_split("text.extract", {"words": True})

    def test_the_flag_reaches_the_engine_call_and_words_are_recorded_in_whole_milliseconds(self):
        model = _Model()
        cues, texts, _info, error = self.worker._segment_cues(model, "tone.wav", "auto", True)
        self.assertEqual(model.seen["word_timestamps"], True)
        self.assertIsNone(error)
        self.assertEqual(cues[0]["words"], [
            {"start_ms": 50, "end_ms": 500, "text": "hello"},
            {"start_ms": 1200, "end_ms": 2000, "text": "there"},
        ])
        self.assertEqual(texts, ["hello there", "second cue"])

    def test_a_segment_only_request_sends_no_flag_and_records_no_words(self):
        model = _Model()
        cues, _texts, _info, _error = self.worker._segment_cues(model, "tone.wav", "auto")
        self.assertEqual(model.seen["word_timestamps"], False)
        self.assertNotIn("words", cues[0])

    def test_window_offsetting_moves_word_times_with_their_cues(self):
        shifted = self.window.offset_cues(
            [{"start_ms": 50, "end_ms": 2000, "text": "hello there",
              "words": [{"start_ms": 50, "end_ms": 500, "text": "hello"},
                        {"start_ms": 1200, "end_ms": 2000, "text": "there"}]}],
            120_000,
        )
        self.assertEqual(shifted[0]["start_ms"], 120_050)
        self.assertEqual([word["start_ms"] for word in shifted[0]["words"]], [120_050, 121_200])
        # a cue with no words stays as it was apart from its own times
        plain = self.window.offset_cues([{"start_ms": 0, "end_ms": 10, "text": "x"}], 1_000)
        self.assertNotIn("words", plain[0])

    def test_a_negative_word_span_after_offsetting_is_an_error_not_a_silent_cue(self):
        with self.assertRaises(ValueError):
            self.window.offset_cues(
                [{"start_ms": 0, "end_ms": 10, "text": "x",
                  "words": [{"start_ms": 5, "end_ms": 1, "text": "broken"}]}],
                0,
            )

    def test_the_worker_command_line_advertises_the_choice(self):
        """Proved against the real process, not against a guessed function signature."""
        completed = subprocess.run(
            [sys.executable, "-B", str(WORKER), "--help"],
            capture_output=True, text=True, encoding="utf-8",
        )
        self.assertEqual(completed.returncode, 0, completed.stderr[-200:])
        self.assertIn("--word-timestamps", completed.stdout)

    @staticmethod
    def _bound_model_dir():
        """Resolve the ASR weights the way the project does, rather than guessing a parent directory.

        A worktree's parent is not the shared root, so path arithmetic from the checkout would skip
        this case even where the model is genuinely bound. `external-resources-index.json` records
        the resolved path of every declared external resource, and a guard test keeps it honest."""
        index = ROOT / "config/environment/external-resources-index.json"
        if not index.is_file():
            return None
        document = json.loads(index.read_text(encoding="utf-8"))
        entries = document.get("entries") or document.get("resources") or []
        for entry in entries:
            if entry.get("name") != "faster-whisper-large-v3-turbo":
                continue
            for path in entry.get("external_paths", []):
                if path.get("exists") and Path(path["resolved"], "model.bin").is_file():
                    return Path(path["resolved"])
        return None

    def test_the_real_model_produces_word_timings_when_the_engine_and_model_are_bound(self):
        """Skipped with a named reason when either is absent, never silently passed.

        The stand-in model proves the wiring; this proves the claim the wiring makes - that the
        declared model can actually deliver word boundaries - on the project's own audio anchor."""
        model_dir = self._bound_model_dir()
        wav = ROOT / "tests/fixtures/golden/golden-audio-anchor.wav"
        try:
            import faster_whisper  # noqa: F401
        except ImportError:
            self.skipTest("faster_whisper is not installed in this lane")
        if model_dir is None:
            self.skipTest("the declared large-v3-turbo weights are not bound in this checkout")
        if not wav.is_file():
            self.skipTest(f"the audio anchor fixture is missing: {wav}")
        out = self.worker.extract(str(wav), str(model_dir), "auto", "cpu", word_timestamps=True)
        params = out["loss_receipt"]["params"]
        self.assertTrue(params["word_timings_requested"])
        self.assertTrue(
            params["word_timings_produced"],
            "the model was asked for word timings and the receipt must not hide whether it gave any",
        )
        words = [word for cue in out["cues"] for word in cue.get("words", [])]
        self.assertTrue(words, "the anchor recording contains speech")
        self.assertTrue(all(word["start_ms"] <= word["end_ms"] for word in words))


if __name__ == "__main__":
    unittest.main()
