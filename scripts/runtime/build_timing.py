"""Per-invocation build stage timing; records failures without command arguments."""
from contextlib import contextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
import time
import uuid

if __package__:
    from . import dev
else:
    import dev


class BuildTimings:
    def __init__(self, artifacts: Path, identity: dict[str, str]):
        self.report = {"schema": "archeaxis.build-timings/v1", "source": {
            name: identity.get(name) for name in ("ARCHEAXIS_SOURCE_COMMIT", "ARCHEAXIS_SOURCE_TREE", "ARCHEAXIS_SOURCE_DIRTY", "ARCHEAXIS_SOURCE_PATCH_SHA256")}, "stages": []}
        artifacts = dev.safe_path(artifacts)
        artifacts.mkdir(parents=True, exist_ok=True)
        while True:
            # Keep names shorter than frontend-build.json for deep Windows runs.
            self.path = dev.safe_path(artifacts / ("bt-" + uuid.uuid4().hex[:8] + ".json"))
            try:
                with self.path.open("x", encoding="utf-8") as output:
                    json.dump(self.report, output)
                break
            except FileExistsError:
                continue

    def save(self):
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(self.report, indent=2) + "\n", encoding="utf-8")
        temporary.replace(self.path)

    @contextmanager
    def stage(self, name):
        item = {"name": name, "started_at": datetime.now(timezone.utc).isoformat(), "status": "RUNNING"}
        self.report["stages"].append(item)
        self.save()
        started = time.perf_counter()
        try:
            yield item
        except BaseException as error:
            item.update(status="FAIL", error_type=type(error).__name__)
            raise
        else:
            item["status"] = "PASS" if item.get("exit_code", 0) == 0 else "FAIL"
        finally:
            item.update(seconds=time.perf_counter() - started, ended_at=datetime.now(timezone.utc).isoformat())
            self.save()
            print(f"[build-timing] {name}: {item['status']} {item['seconds']:.3f}s; {self.path}", flush=True)
