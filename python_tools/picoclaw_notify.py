#!/usr/bin/env python3
"""Shared Picoclaw notification helpers for skills."""

from __future__ import annotations


def notify_image(path_output: str, message: str | None = None) -> bool:
    """Best-effort notify Picoclaw with image and optional message."""
    try:
        import picoclaw  # type: ignore
    except Exception:
        return False

    sent_any = False

    try:
        send_file = getattr(picoclaw, "send_file", None)
        if callable(send_file):
            send_file(path_output)
            sent_any = True
    except Exception as e:
        print(f"[PICOCLAW] send_file failed: {e}")

    try:
        send_msg = getattr(picoclaw, "message", None) or getattr(picoclaw, "send_message", None)
        if callable(send_msg):
            send_msg(message or f"2K image captured: {path_output}")
            sent_any = True
    except Exception as e:
        print(f"[PICOCLAW] message failed: {e}")

    return sent_any
