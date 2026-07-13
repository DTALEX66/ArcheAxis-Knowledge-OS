"""Unified logging for Cognitive-Loop-OS.

Uses loguru for structured JSON logging.
Drop-in replacement for print() calls across the project:

    from shared.logging import logger
    logger.info("route decided: {}", decision.route)
    logger.error("conversion failed: {}", e)
"""

from __future__ import annotations

import sys

from shared.config import config, resolve_runtime_path

try:
    from loguru import logger
except ImportError:
    # Fallback to stdlib logging if loguru not installed
    import logging as _logging

    logger = _logging.getLogger("cognitive-os")  # type: ignore[assignment]
else:
    # Remove default handler
    logger.remove()

    if bool(config.get("logging.console", True)):
        logger.add(
            sys.stderr,
            format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> | <level>{message}</level>",
            level=str(config.get("logging.level", "INFO")),
            colorize=True,
        )

    if bool(config.get("logging.file", True)):
        _log_dir = resolve_runtime_path(str(config.get("logging.file_dir", "data/logs")))
        _log_dir.mkdir(parents=True, exist_ok=True)
        logger.add(
            _log_dir / "cognitive_os_{time:YYYY-MM-DD}.jsonl",
            format="{time} {level} {name} {function} {message} {extra}",
            level=str(config.get("logging.level", "INFO")),
            rotation=str(config.get("logging.rotation", "10 MB")),
            retention=str(config.get("logging.retention", "7 days")),
            serialize=True,
        )
