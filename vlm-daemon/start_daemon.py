#!/usr/bin/env python3
"""Start the VLM daemon."""

from daemon_control import start_daemon


if __name__ == "__main__":
    raise SystemExit(start_daemon())