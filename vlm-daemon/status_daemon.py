#!/usr/bin/env python3
"""Print the VLM daemon status."""

from daemon_control import print_status


if __name__ == "__main__":
    raise SystemExit(print_status())