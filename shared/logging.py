"""Unified logging for Cognitive-Loop-OS.

Uses loguru for structured JSON logging.
Drop-in replacement for print() calls across the project:

    from shared.logging import logger
    logger.info("route decided: {}", decision.route)
    logger.error("conversion failed: {}", e)
"""
from __future__ import annotations

import sys
from pathlib import Path

try:
    from loguru import logger
except ImportError:
    # Fallback to stdlib logging if loguru not installed
    import logging as _logging
    logger = _logging.getLogger("cognitive-os")  # type: ignore[assignment]
else:
    # Remove default handler
    logger.remove()

    # Console: human-readable colors for dev
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> | <level>{message}</level>",
        level="DEBUG",
        colorize=True,
    )

    # File: structured JSON for production
    _log_dir = Path(__file__).resolve().parents[1] / "data" / "logs"
    _log_dir.mkdir(parents=True, exist_ok=True)
    logger.add(
        _log_dir / "cognitive_os_{time:YYYY-MM-DD}.jsonl",
        format="{time} {level} {name} {function} {message} {extra}",
        level="INFO",
        rotation="10 MB",
        retention="7 days",
        serialize=True,  # JSON output
    )

    logger.info("Logger initialized — console + JSON file ({})", _log_dir)
