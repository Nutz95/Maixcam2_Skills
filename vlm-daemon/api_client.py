#!/usr/bin/env python3
"""Small CLI client for the local VLM daemon API."""

import argparse
import json
import urllib.error
import urllib.request


def http_json(method: str, url: str, payload=None):
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url=url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code}: {body}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Network error: {e.reason}") from e


def main():
    parser = argparse.ArgumentParser(description="VLM daemon API client")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=18080)

    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("health")
    sub.add_parser("models")

    p_load = sub.add_parser("load")
    p_load.add_argument("--model", required=True)
    p_load.add_argument("--model-path", default=None)
    p_load.add_argument("--system-prompt", default=None)

    sub.add_parser("unload")

    p_capture = sub.add_parser("capture")
    p_capture.add_argument("--output-path", default=None)

    p_ask = sub.add_parser("ask")
    p_ask.add_argument("--question", required=True)
    p_ask.add_argument("--capture-new", action="store_true")
    p_ask.add_argument("--output-path", default=None)
    p_ask.add_argument("--image-path", default=None)

    parser.add_argument("--pretty", action="store_true", help="Pretty print JSON output")

    args = parser.parse_args()
    base = f"http://{args.host}:{args.port}"

    if args.cmd == "health":
        result = http_json("GET", base + "/health")
    elif args.cmd == "models":
        result = http_json("GET", base + "/models")
    elif args.cmd == "load":
        payload = {
            "model": args.model,
            "model_path": args.model_path,
            "system_prompt": args.system_prompt,
        }
        result = http_json("POST", base + "/models/load", payload=payload)
    elif args.cmd == "unload":
        result = http_json("POST", base + "/models/unload", payload={})
    elif args.cmd == "capture":
        payload = {"output_path": args.output_path}
        result = http_json("POST", base + "/capture", payload=payload)
    elif args.cmd == "ask":
        payload = {
            "question": args.question,
            "capture_new": bool(args.capture_new),
            "output_path": args.output_path,
            "image_path": args.image_path,
        }
        result = http_json("POST", base + "/ask", payload=payload)
    else:
        raise RuntimeError(f"Unsupported command: {args.cmd}")

    if args.pretty:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
