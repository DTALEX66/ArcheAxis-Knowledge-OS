"""Safe file writer for archeaxis-workspace.

Adapted from Obsidian-Assistance V4 SafeVaultWriter.
Generalized for project-local file operations:
- Dry-run by default; explicit --apply required for writes.
- Backs up existing files before overwrite.
- Blocks path traversal (writes outside project root).
- Generates a write plan/report for audit.
"""

from __future__ import annotations

import datetime as _dt
import json
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path

from shared.approved_paths import ApprovedRoots, ApprovedRootsError


@dataclass
class WriteItem:
    relative_path: str
    target_path: str
    bytes: int
    action: str  # "create" or "overwrite"
    backup_path: str | None = None


class SafeWriter:
    """Project-local safe file writer.

    Usage:
        writer = SafeWriter(project_root=".", dry_run=True)
        writer.apply_write("KB/new_doc.md", content)
        report = writer.write_report()
        # After review:
        writer.dry_run = False
        writer.apply_write("KB/new_doc.md", content)
    """

    def __init__(
        self,
        project_root: str | Path = ".",
        backup_dir: str | Path | None = None,
        dry_run: bool = True,
        approved_roots: ApprovedRoots | None = None,
    ):
        self.project_root = Path(project_root).expanduser().resolve()
        if not self.project_root.exists():
            raise ValueError(f"project_root does not exist: {self.project_root}")

        if backup_dir is None:
            backup_dir = (
                self.project_root
                / ".safe_writer_backups"
                / _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
            )
        self.approved_roots = approved_roots or ApprovedRoots(output_roots=[self.project_root])
        self.backup_dir = Path(backup_dir).expanduser().resolve()
        try:
            self.backup_dir = self.approved_roots.resolve_output(self.backup_dir)
        except ApprovedRootsError as exc:
            raise ValueError(f"backup_dir outside approved output roots: {self.backup_dir}") from exc
        self.dry_run = dry_run
        self.items: list[WriteItem] = []

    def _resolve_inside_project(self, relative_path: str | Path) -> Path:
        """Resolve relative path and enforce it stays inside project root."""
        rel = Path(relative_path)
        if rel.is_absolute():
            raise ValueError(f"relative_path must not be absolute: {relative_path}")
        try:
            return self.approved_roots.resolve_output(rel)
        except ApprovedRootsError as exc:
            raise ValueError(f"path traversal blocked: {relative_path}") from exc

    def _backup_existing(self, target: Path) -> Path:
        """Copy existing file to backup directory."""
        try:
            rel = self.approved_roots.relative_output(target)
            backup_path = self.approved_roots.resolve_output(self.backup_dir / rel)
        except ApprovedRootsError as exc:
            raise ValueError("backup target outside approved output roots") from exc
        if not self.dry_run:
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, backup_path)
        return backup_path

    def apply_write(self, relative_path: str | Path, content: str) -> WriteItem:
        """Plan (dry-run) or execute a file write with backup.

        Args:
            relative_path: Path relative to project_root to write to.
            content: Text content to write (UTF-8, LF newlines).
        Returns:
            WriteItem describing the action taken/planned.
        """
        target = self._resolve_inside_project(relative_path)
        action = "overwrite" if target.exists() else "create"
        backup_path: str | None = None

        if target.exists():
            backup_path = str(self._backup_existing(target))

        item = WriteItem(
            relative_path=str(relative_path),
            target_path=str(target),
            bytes=len(content.encode("utf-8")),
            action=action,
            backup_path=backup_path,
        )
        self.items.append(item)

        if not self.dry_run:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8", newline="\n")

        return item

    def write_report(self) -> dict:
        """Generate a JSON plan + Markdown report in backup_dir.

        Returns:
            Dict with plan, plan_path, report_path.
        """
        plan = {
            "dry_run": self.dry_run,
            "project_root": str(self.project_root),
            "backup_dir": str(self.backup_dir),
            "items": [asdict(i) for i in self.items],
        }

        if self.dry_run:
            return {
                "plan": plan,
                "plan_path": None,
                "report_path": None,
                "note": "Dry-run only. No files written. Set dry_run=False to apply.",
            }

        self.backup_dir.mkdir(parents=True, exist_ok=True)

        plan_path = self.backup_dir / "write-plan.json"
        plan_path.write_text(
            json.dumps(plan, ensure_ascii=False, indent=2),
            encoding="utf-8",
            newline="\n",
        )

        report_path = self.backup_dir / "write-report.md"
        lines = [
            "# Safe Writer Report",
            "",
            f"- **Project root**: `{self.project_root}`",
            f"- **Dry run**: `{self.dry_run}`",
            f"- **Backup dir**: `{self.backup_dir}`",
            "",
            "| Action | Relative Path | Bytes | Backup |",
            "|---|---|---:|---|",
        ]
        for i in self.items:
            lines.append(
                f"| {i.action} | `{i.relative_path}` | {i.bytes} | `{i.backup_path or ''}` |"
            )
        report_path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

        return {
            "plan": plan,
            "plan_path": str(plan_path),
            "report_path": str(report_path),
        }


# ── Convenience CLI entry point ──


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Safe writer for archeaxis-workspace project files")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--relative-path", required=True)
    parser.add_argument("--content-file", required=True)
    parser.add_argument("--backup-dir", default=None)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    content = Path(args.content_file).read_text(encoding="utf-8")
    writer = SafeWriter(
        project_root=args.project_root,
        backup_dir=args.backup_dir,
        dry_run=not args.apply,
    )
    writer.apply_write(args.relative_path, content)
    result = writer.write_report()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
