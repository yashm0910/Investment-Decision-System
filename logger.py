from __future__ import annotations

import logging
import sys
from pathlib import Path
from datetime import datetime

'''
Change made for deployment:
- Removed runtime dependency on writable /app/logs.
- Switched production logging to StreamHandler(stdout), which is safe for read-only container filesystems.
- Kept the old file-based logging code commented out for reference.
'''

# Use /tmp because /app is read-only in deployment environments.
LOG_DIR = Path("/tmp/logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

def get_logger(name: str) -> logging.Logger:
    """
    Returns a module-specific logger.
    Each module gets its own daily log file:
        logs/research_agent_YYYY-MM-DD.log
        logs/db_YYYY-MM-DD.log
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    logger.propagate = False

    today = datetime.now().strftime("%Y-%m-%d")
    log_path = LOG_DIR / f"{name}_{today}.log"

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Old file-based logging kept for reference:
    # file_handler = RotatingFileHandler(
    #     log_path,
    #     maxBytes=5 * 1024 * 1024,
    #     backupCount=5,
    #     encoding="utf-8",
    # )
    # file_handler.setFormatter(formatter)
    # file_handler.setLevel(logging.INFO)
    #
    # logger.addHandler(file_handler)

    # New deployment-safe logging: write to stdout instead of the filesystem.
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(logging.INFO)

    logger.addHandler(stream_handler)

    return logger
