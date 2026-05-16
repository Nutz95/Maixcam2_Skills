#!/usr/bin/env python3
"""Stop the VLM daemon."""

from daemon_control import stop_daemon


if __name__ == "__main__":
    raise SystemExit(stop_daemon())