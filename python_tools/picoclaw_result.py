#!/usr/bin/env python3
"""Shared output helpers to guide PicoClaw text/media delivery."""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, Optional


def write_report_file(base_dir: str, text: str, prefix: str = "report") -> str:
    """Write a text report file and return its path (use only when a persistent file is needed)."""
    os.makedirs(base_dir, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    report_path = os.path.join(base_dir, f"{prefix}_{ts}.txt")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(text)
        f.write("\n")
    return report_path


def emit_picoclaw_markers(
    result: Dict[str, Any],
    *,
    answer_key: str = "answer",
    image_key: str = "image_path",
    default_base_dir: str = "/root/.picoclaw/workspace",
    report_prefix: str = "report",
) -> Dict[str, Optional[str]]:
    """Emit IMAGE_FILE / SEND_POLICY / PICOCLAW_RESULT_JSON markers.

    The answer is printed as plain inline text so PicoClaw forwards it as a
    chat message (not as a file attachment). The image is referenced via
    IMAGE_FILE so it is sent as a photo alongside the message.

    Returns a summary dict for callers that need structured access.
    """
    if not isinstance(result, dict):
        return {
            "image_file": None,
            "answer": None,
            "send_policy": "report_only",
        }

    answer = str(result.get(answer_key) or "").strip()
    image_path = str(result.get(image_key) or "").strip()

    # Print answer as plain text — PicoClaw / the LLM reads stdout and
    # includes this in the Telegram chat message (no file attachment).
    if answer:
        print(answer)

    if image_path:
        print(f"IMAGE_FILE: {image_path}")

    send_policy = "report_and_image" if (answer and image_path) else (
        "image_only" if image_path else "report_only"
    )
    print(f"SEND_POLICY: {send_policy}")

    summary: Dict[str, Optional[str]] = {
        "image_file": image_path if image_path else None,
        "answer": answer if answer else None,
        "send_policy": send_policy,
    }
    print("PICOCLAW_RESULT_JSON=" + json.dumps(summary, ensure_ascii=False))
    return summary
