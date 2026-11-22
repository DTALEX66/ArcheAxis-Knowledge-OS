"""Run machine.answer with the SDK available for the bundle's registered local model."""

import runpy
from pathlib import Path

if __name__ == "__main__":
    runpy.run_path(
        str(Path(__file__).with_name("worker_machine_answer.py")),
        run_name="__main__",
        init_globals={"PACKAGED_FAST_LOCAL": "auto"},
    )
