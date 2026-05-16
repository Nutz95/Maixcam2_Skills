#!/usr/bin/env python3
"""Python-native control CLI for the local VLM daemon."""

from __future__ import annotations

import argparse
import json

from daemon_control import HOST, PORT, http_json, print_status, start_daemon, stop_daemon
from python_tools.picoclaw_result import emit_picoclaw_markers


def main() -> int:
    parser = argparse.ArgumentParser(description="VLM daemon control")
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument("--pretty", action="store_true", help="Pretty print JSON output")

    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("start")
    sub.add_parser("stop")
    sub.add_parser("status")
    sub.add_parser("health")
    sub.add_parser("models")

    p_load = sub.add_parser("load")
    p_load.add_argument("model")
    p_load.add_argument("--model-path", default=None)
    p_load.add_argument("--system-prompt", default=None)

    sub.add_parser("unload")

    p_capture = sub.add_parser("capture")
    p_capture.add_argument("output_path", nargs="?", default=None)

    p_ask = sub.add_parser("ask")
    p_ask.add_argument("question", nargs="+")
    p_ask.add_argument("--output-path", default=None)

    p_describe = sub.add_parser("describe")
    p_describe.add_argument(
        "--question",
        default="Describe the scene in one sentence.",
        help="Question to ask after capture (defaults to a scene description request)",
    )
    p_describe.add_argument("--output-path", default=None)

    p_ask_image = sub.add_parser("ask-image")
    p_ask_image.add_argument("image_path")
    p_ask_image.add_argument("question", nargs="+")

    args = parser.parse_args()

    if args.cmd == "start":
        return start_daemon()
    if args.cmd == "stop":
        return stop_daemon()
    if args.cmd == "status":
        return print_status()

    base = f"http://{args.host}:{args.port}"
    if args.cmd == "health":
        result = http_json("GET", base + "/health")
    elif args.cmd == "models":
        result = http_json("GET", base + "/models")
    elif args.cmd == "load":
        result = http_json(
            "POST",
            base + "/models/load",
            payload={
                "model": args.model,
                "model_path": args.model_path,
                "system_prompt": args.system_prompt,
            },
        )
    elif args.cmd == "unload":
        result = http_json("POST", base + "/models/unload", payload={})
    elif args.cmd == "capture":
        result = http_json("POST", base + "/capture", payload={"output_path": args.output_path})
    elif args.cmd == "ask":
        question = " ".join(args.question)
        result = http_json(
            "POST",
            base + "/ask",
            payload={
                "question": question,
                "capture_new": True,
                "output_path": args.output_path,
                "image_path": None,
            },
        )
    elif args.cmd == "describe":
        result = http_json(
            "POST",
            base + "/ask",
            payload={
                "question": args.question,
                "capture_new": True,
                "output_path": args.output_path,
                "image_path": None,
            },
        )
    elif args.cmd == "ask-image":
        question = " ".join(args.question)
        result = http_json(
            "POST",
            base + "/ask",
            payload={
                "question": question,
                "capture_new": False,
                "output_path": None,
                "image_path": args.image_path,
            },
        )
    else:
        raise RuntimeError(f"Unsupported command: {args.cmd}")

    output_result = result
    if args.cmd == "describe" and isinstance(result, dict):
        # For describe, keep stdout strictly text-focused: do not expose
        # image_path in the raw JSON line to avoid media re-forwarding.
        output_result = dict(result)
        output_result.pop("image_path", None)
        output_result["send_policy"] = "report_only"

    if args.pretty:
        print(json.dumps(output_result, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(output_result, ensure_ascii=False))

    if args.cmd in ("ask", "ask-image", "capture", "describe"):
        marker_image_key = "__never_image__" if args.cmd == "describe" else "image_path"
        emit_picoclaw_markers(
            result,
            image_key=marker_image_key,
            report_prefix="vlm_report",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())