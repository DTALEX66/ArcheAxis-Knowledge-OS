"""Media extraction adapters — adapted from Obsidian-Assistance v6.

PDF page snapshots + video keyframe extraction.
Requires optional dependencies: PyMuPDF (for PDF) and ffmpeg (for video).
Gracefully falls back when not installed.

Adapted from: scripts/v6/pdf_page_snapshot.py + video_keyframe_extract.py
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from shared.approved_paths import ApprovedRoots, ApprovedRootsError

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_APPROVED_ROOTS = ApprovedRoots(source_roots=[_PROJECT_ROOT], output_roots=[_PROJECT_ROOT / "data"])


def extract_pdf_pages(
    pdf_path: str,
    output_dir: str = "",
    pages: list[int] | None = None,
    dpi: int = 150,
    approved_roots: ApprovedRoots | None = None,
) -> dict[str, Any]:
    """Extract pages from a PDF as PNG images.

    Requires: pip install PyMuPDF

    Args:
        pdf_path: path to PDF file.
        output_dir: directory for output images (default: PDF dir).
        pages: specific page numbers (1-indexed). None = first 5.
        dpi: resolution.

    Returns:
        {pdf, pages_extracted, output_files: [...]}.
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        return {"error": "PyMuPDF not installed. Run: pip install PyMuPDF", "pdf": pdf_path}

    policy = approved_roots or _APPROVED_ROOTS
    try:
        pdf_file = policy.resolve_source(pdf_path)
        out_dir = policy.resolve_output(output_dir or "media")
    except ApprovedRootsError as exc:
        return {"error": str(exc), "pdf": pdf_path}
    if not pdf_file.exists():
        return {"error": "PDF not found", "pdf": pdf_path}

    out_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(str(pdf_file))
    if pages is None:
        pages = list(range(min(5, len(doc))))

    output_files = []
    for page_num in pages:
        if page_num >= len(doc):
            continue
        page = doc[page_num]
        pix = page.get_pixmap(dpi=dpi)
        out_path = out_dir / f"{pdf_file.stem}_p{page_num + 1:03d}.png"
        pix.save(str(out_path))
        output_files.append(str(out_path))

    doc.close()

    return {
        "pdf": pdf_path,
        "total_pages": len(doc) if "doc" in dir() else 0,
        "pages_extracted": len(output_files),
        "output_files": output_files,
    }


def extract_video_keyframes(
    video_path: str,
    output_dir: str = "",
    interval_seconds: float = 30,
    max_frames: int = 10,
    approved_roots: ApprovedRoots | None = None,
) -> dict[str, Any]:
    """Extract keyframes from a video using ffmpeg.

    Requires: ffmpeg in PATH

    Args:
        video_path: path to video file.
        output_dir: directory for output frames.
        interval_seconds: extract one frame every N seconds.
        max_frames: max frames to extract.

    Returns:
        {video, frames_extracted, output_files: [...]}.
    """
    import shutil
    import subprocess

    if not shutil.which("ffmpeg"):
        return {"error": "ffmpeg not found in PATH. Install ffmpeg first.", "video": video_path}

    policy = approved_roots or _APPROVED_ROOTS
    try:
        video_file = policy.resolve_source(video_path)
        out_dir = policy.resolve_output(output_dir or "media/keyframes")
    except ApprovedRootsError as exc:
        return {"error": str(exc), "video": video_path}
    if not video_file.exists():
        return {"error": "Video not found", "video": video_path}

    out_dir.mkdir(parents=True, exist_ok=True)

    output_pattern = str(out_dir / f"{video_file.stem}_frame_%03d.png")

    try:
        subprocess.run(
            [
                "ffmpeg",
                "-i",
                str(video_file),
                "-vf",
                f"fps=1/{interval_seconds}",
                "-vframes",
                str(max_frames),
                "-q:v",
                "2",
                output_pattern,
                "-y",
                "-loglevel",
                "error",
            ],
            check=True,
            timeout=120,
        )

        output_files = sorted(out_dir.glob(f"{video_file.stem}_frame_*.png"))
        return {
            "video": video_path,
            "frames_extracted": len(output_files),
            "output_files": [str(f) for f in output_files],
        }
    except subprocess.TimeoutExpired:
        return {"error": "ffmpeg timed out", "video": video_path}
    except subprocess.CalledProcessError as e:
        return {"error": f"ffmpeg failed: {e}", "video": video_path}


def media_inventory(source_dir: str) -> dict[str, Any]:
    """Scan a directory for PDFs and videos, return inventory for processing.

    Returns:
        {pdfs: [...], videos: [...], total_size_mb}.
    """
    from shared.source_discovery import discover_sources

    discovery = discover_sources(source_dir, max_files=50)

    pdfs = []
    videos = []

    for f in discovery.get("files", []):
        if f["type"] in ("pdf", "slides", "document"):
            pdfs.append(f)
        elif f["type"] == "video":
            videos.append(f)

    return {
        "source_dir": source_dir,
        "pdf_count": len(pdfs),
        "video_count": len(videos),
        "pdfs": pdfs[:10],
        "videos": videos[:10],
    }
