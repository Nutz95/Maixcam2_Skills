#!/usr/bin/env python3
"""Shared MaixPy runtime environment helpers."""

from __future__ import annotations

import os
import sys

REQUIRED_LD_PATHS = [
    "/usr/local/lib",
    "/usr/lib",
    "/opt/lib",
    "/opt/usr/lib",
    "/soc/lib",
]


def ensure_maix_env() -> None:
    """Ensure LD_LIBRARY_PATH is compatible with MaixPy native libs."""
    current = os.environ.get("LD_LIBRARY_PATH", "")
    current_parts = [p for p in current.split(":") if p]

    merged = []
    for path in REQUIRED_LD_PATHS + current_parts:
        if path not in merged:
            merged.append(path)

    target = ":".join(merged)
    if current != target:
        # Re-exec so dynamic linker sees updated env before importing maix.
        env = os.environ.copy()
        env["LD_LIBRARY_PATH"] = target
        os.execve(sys.executable, [sys.executable] + sys.argv, env)
