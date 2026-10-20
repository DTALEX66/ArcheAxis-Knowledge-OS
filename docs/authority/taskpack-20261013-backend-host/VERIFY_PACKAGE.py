from pathlib import Path
import hashlib, json, sys
root = Path(__file__).resolve().parent
manifest = json.loads((root / "CHECKSUMS.json").read_text(encoding="utf8"))
errors = []
for item in manifest["files"]:
    p = root / item["path"]
    if not p.is_file():
        errors.append("missing: " + item["path"])
        continue
    raw = p.read_bytes()
    if len(raw) != item["bytes"] or hashlib.sha256(raw).hexdigest() != item["sha256"]:
        errors.append("changed: " + item["path"])
if errors:
    print("\n".join(errors)); sys.exit(1)
print("PASS: " + str(len(manifest["files"])) + " packaged files match SHA-256 and size; product runtime not tested")
