#!/usr/bin/env python3

### Disclaimer
# This file is generated with the help of Junie. It is not meant for production use. If there are any mistakes or misinformation, please summit an issue [here](https://github.com/Cheukting/BuildingAIAgent/issues).
###

"""
End-to-end test script for Exercise_2 web app/agent.

Features:
- Runs a simple conversation flow against the FastAPI app:
  1) Initial search prompt
  2) Optional "more"
  3) Optional "details 1"
  4) "restart"
- Records each step's input, start/end timestamps, duration (ms), HTTP status, and a compact
  summary of the response into a JSONL log file under Exercise_3/logs/.
- Can target a running server via --server-url, or use FastAPI TestClient in-process.
- Detects llamafile backend readiness issues (HTTP 503) and reports clearly.

Usage examples:
  python Exercise_3/e2e_test.py --prompt "lighthearted sci-fi from the 90s"
  python Exercise_3/e2e_test.py --server-url http://127.0.0.1:8000 --prompt "romantic comedy 2005"

Prerequisites:
- llamafile LLM server must be running and reachable at LLAMAFILE_BASE_URL (see Exercise_2/config.py).
  Example: ./Qwen2.5-0.5B-Instruct-Q6_K.llamafile --server --port 8080
- Internet connectivity for iTunes/Wikipedia lookups.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def compact_response(resp_json: Dict[str, Any]) -> Dict[str, Any]:
    # Keep only a compact summary for logging
    results = resp_json.get("results") or []
    return {
        "status": resp_json.get("status"),
        "message": (resp_json.get("message") or "")[:180],
        "filters": resp_json.get("filters"),
        "page": resp_json.get("page"),
        "has_more": resp_json.get("has_more"),
        "results_count": len(results),
        "first_titles": [r.get("title") for r in results[:3]],
    }


def write_jsonl_line(path: Path, obj: Dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def call_api(input_text: str, server_url: Optional[str]):
    start_ns = time.perf_counter_ns()
    if server_url:
        import requests
        url = server_url.rstrip("/") + "/api/message"
        resp = requests.post(url, json={"input": input_text}, timeout=60)
        duration_ms = (time.perf_counter_ns() - start_ns) / 1e6
        try:
            data = resp.json()
        except Exception:
            data = {"raw_text": resp.text}
        return resp.status_code, duration_ms, data
    else:
        # Use in-process TestClient
        try:
            from Exercise_2.web_app import app  # type: ignore
            from fastapi.testclient import TestClient
        except Exception as e:
            raise RuntimeError(f"Failed to import app/TestClient: {e}")
        client = TestClient(app)
        resp = client.post("/api/message", json={"input": input_text})
        duration_ms = (time.perf_counter_ns() - start_ns) / 1e6
        data = resp.json() if resp.content else {}
        return resp.status_code, duration_ms, data


def main():
    parser = argparse.ArgumentParser(description="E2E test for Exercise_2 agent")
    parser.add_argument("--prompt", default="lighthearted sci-fi from the 90s", help="Initial user prompt")
    parser.add_argument("--server-url", default=None, help="Base URL of running web server (e.g., http://127.0.0.1:8000). If omitted, uses in-process TestClient.")
    parser.add_argument("--no-more", action="store_true", help="Skip the 'more' step")
    parser.add_argument("--no-details", action="store_true", help="Skip the 'details 1' step")
    parser.add_argument("--log-prefix", default="e2e_log", help="Prefix for log filename")

    args = parser.parse_args()

    log_file = LOG_DIR / f"{args.log_prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"

    print(f"[E2E] Starting at {now_iso()} | log -> {log_file}")
    print(f"[E2E] Using server: {args.server_url or 'in-process TestClient'}")

    steps = [
        (args.prompt, "initial"),
    ]
    if not args.no_more:
        steps.append(("more", "more"))
    if not args.no_details:
        steps.append(("details 1", "details"))
    steps.append(("restart", "restart"))

    run_meta = {
        "started_at": now_iso(),
        "server_url": args.server_url or "in-process",
        "prompt": args.prompt,
        "env_LLAMAFILE_BASE_URL": os.getenv("LLAMAFILE_BASE_URL"),
    }
    write_jsonl_line(log_file, {"type": "run_start", **run_meta})

    for text, label in steps:
        t0 = datetime.now().isoformat(timespec="seconds")
        status, dur_ms, payload = call_api(text, args.server_url)
        t1 = datetime.now().isoformat(timespec="seconds")

        # Extract filters at top-level for easier analysis (also present inside response)
        filters = payload.get("filters") if isinstance(payload, dict) else None

        row = {
            "type": "step",
            "label": label,
            "input": text,
            "started_at": t0,
            "ended_at": t1,
            "duration_ms": round(dur_ms, 2),
            "http_status": status,
            "filters": filters,
            "response": compact_response(payload) if isinstance(payload, dict) else {"raw": str(payload)[:200]},
        }
        print(f"[E2E] {label}: {status} in {row['duration_ms']} ms | results={row['response'].get('results_count')}")
        if status == 503:
            print("[E2E] LLM backend not ready (503). Ensure llamafile server is running and LLAMAFILE_BASE_URL is set.")
        write_jsonl_line(log_file, row)

    write_jsonl_line(log_file, {"type": "run_end", "ended_at": now_iso()})
    print(f"[E2E] Done. Log saved to {log_file}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[E2E] Interrupted.")
        sys.exit(1)
