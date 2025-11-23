#!/usr/bin/env python3

### Disclaimer
# This file is generated with the help of Junie. It is not meant for production use. If there are any mistakes or misinformation, please summit an issue [here](https://github.com/Cheukting/BuildingAIAgent/issues).
###

"""
Benchmark script for Exercise_2 agent via FastAPI.

- Runs a set of prompts multiple times (configurable), either against a provided
  server URL or using FastAPI TestClient in-process.
- Records per-run measurements (duration, status, results count) to JSONL logs.
- Emits an aggregated summary JSON with basic stats (avg/median p50/p95, success rate).

Usage examples:
  python Exercise_3/benchmark.py --repeats 3 --prompts-file Exercise_3/test_cases.json
  python Exercise_3/benchmark.py --server-url http://127.0.0.1:8000 --repeats 5

Notes:
- LLM backend (llamafile) must be running and reachable per Exercise_2/config.py.
- Internet connectivity is required.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)


def call_api(input_text: str, server_url: Optional[str]) -> Tuple[int, float, Dict[str, Any]]:
    start_ns = time.perf_counter_ns()
    if server_url:
        import requests
        url = server_url.rstrip("/") + "/api/message"
        resp = requests.post(url, json={"input": input_text}, timeout=60)
        dur_ms = (time.perf_counter_ns() - start_ns) / 1e6
        try:
            data = resp.json()
        except Exception:
            data = {"raw_text": resp.text}
        return resp.status_code, dur_ms, data
    else:
        from Exercise_2.web_app import app  # type: ignore
        from fastapi.testclient import TestClient
        client = TestClient(app)
        resp = client.post("/api/message", json={"input": input_text})
        dur_ms = (time.perf_counter_ns() - start_ns) / 1e6
        data = resp.json() if resp.content else {}
        return resp.status_code, dur_ms, data


def load_prompts(path: Optional[str]) -> List[str]:
    if not path:
        return [
            "lighthearted sci-fi from the 90s",
            "romantic comedy around 2005",
            "thrillers with DiCaprio",
            "family friendly animation recent",
        ]
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Prompts file not found: {path}")
    with p.open("r", encoding="utf-8") as f:
        arr = json.load(f)
    if isinstance(arr, dict) and "prompts" in arr:
        arr = arr["prompts"]
    if not isinstance(arr, list):
        raise ValueError("Prompts file must be a JSON list or an object with 'prompts' list.")
    return [str(x) for x in arr]


def percentile(values: List[float], p: float) -> float:
    if not values:
        return math.nan
    values_sorted = sorted(values)
    k = (len(values_sorted) - 1) * (p / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return values_sorted[int(k)]
    d0 = values_sorted[int(f)] * (c - k)
    d1 = values_sorted[int(c)] * (k - f)
    return d0 + d1


def main():
    parser = argparse.ArgumentParser(description="Benchmark Exercise_2 agent")
    parser.add_argument("--server-url", default=None, help="Server base URL. If omitted, uses in-process TestClient.")
    parser.add_argument("--prompts-file", default=str(Path(__file__).parent / "test_cases.json"), help="JSON file with a list of prompts or {prompts: [...]}")
    parser.add_argument("--repeats", type=int, default=3, help="Number of repetitions per prompt")
    parser.add_argument("--log-prefix", default="bench_runs", help="Log filename prefix")

    args = parser.parse_args()

    prompts = load_prompts(args.prompts_file)

    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    jsonl_path = LOG_DIR / f"{args.log_prefix}_{ts}.jsonl"
    summary_path = LOG_DIR / f"{args.log_prefix}_{ts}_summary.json"

    meta = {
        "started_at": datetime.now().isoformat(timespec="seconds"),
        "server_url": args.server_url or "in-process",
        "repeats": args.repeats,
        "prompts_count": len(prompts),
        "env_LLAMAFILE_BASE_URL": os.getenv("LLAMAFILE_BASE_URL"),
    }

    with jsonl_path.open("w", encoding="utf-8") as jf:
        jf.write(json.dumps({"type": "meta", **meta}) + "\n")

    all_durations: Dict[str, List[float]] = {p: [] for p in prompts}
    all_status: Dict[str, List[int]] = {p: [] for p in prompts}
    all_counts: Dict[str, List[int]] = {p: [] for p in prompts}

    print(f"[BENCH] Prompts={len(prompts)} repeats={args.repeats} server={args.server_url or 'in-process'}")

    for prompt in prompts:
        for i in range(args.repeats):
            # Ensure clean state before each run by restarting the agent
            r_status, r_dur_ms, r_payload = call_api("restart", args.server_url)
            r_filters = r_payload.get("filters") if isinstance(r_payload, dict) else None
            with jsonl_path.open("a", encoding="utf-8") as jf:
                jf.write(json.dumps({
                    "type": "restart",
                    "prompt": prompt,
                    "iteration": i + 1,
                    "status": r_status,
                    "duration_ms": round(r_dur_ms, 2),
                    "filters": r_filters,
                }, ensure_ascii=False) + "\n")

            status, dur_ms, payload = call_api(prompt, args.server_url)
            results = payload.get("results") if isinstance(payload, dict) else None
            count = len(results) if isinstance(results, list) else None
            filters = payload.get("filters") if isinstance(payload, dict) else None
            row = {
                "type": "run",
                "prompt": prompt,
                "iteration": i + 1,
                "status": status,
                "duration_ms": round(dur_ms, 2),
                "results_count": count,
                "filters": filters,
            }
            with jsonl_path.open("a", encoding="utf-8") as jf:
                jf.write(json.dumps(row, ensure_ascii=False) + "\n")

            if count is not None:
                all_counts[prompt].append(count)
            all_durations[prompt].append(dur_ms)
            all_status[prompt].append(status)

            note = ""
            if status == 503:
                note = " (LLM backend not ready)"
            print(f"[BENCH] '{prompt}' #{i+1}: {status} in {row['duration_ms']} ms, results={count}{note}")

    # Build summary
    summary: Dict[str, Any] = {
        "meta": meta,
        "prompts": [],
        "totals": {},
    }

    all_ms: List[float] = []
    all_success_status_only: int = 0
    all_success_ideal_results: int = 0
    all_total: int = 0

    for prompt in prompts:
        durs = all_durations[prompt]
        status_list = all_status[prompt]
        counts_list = all_counts[prompt]
        runs_count = len(status_list)

        success_status_only = sum(1 for s in status_list if 200 <= s < 300)
        # Ideal results: status 2xx AND results_count between 5 and 10 inclusive
        success_ideal_results = 0
        for idx, s in enumerate(status_list):
            c = counts_list[idx] if idx < len(counts_list) else None
            if 200 <= s < 300 and c is not None and 5 <= c <= 10:
                success_ideal_results += 1

        stats = {
            "runs": len(durs),
            "avg_ms": round(statistics.mean(durs), 2) if durs else None,
            "p50_ms": round(percentile(durs, 50), 2) if durs else None,
            "p95_ms": round(percentile(durs, 95), 2) if durs else None,
            "min_ms": round(min(durs), 2) if durs else None,
            "max_ms": round(max(durs), 2) if durs else None,
            # Keep backward compatibility: original success_rate (status only)
            "success_rate": round(success_status_only / max(1, runs_count), 3),
            # Explicit names for clarity
            "success_rate_status_only": round(success_status_only / max(1, runs_count), 3),
            "success_rate_ideal_results": round(success_ideal_results / max(1, runs_count), 3),
            "avg_results": round(statistics.mean(counts_list), 2) if counts_list else None,
        }
        summary["prompts"].append({"prompt": prompt, **stats})
        all_ms.extend(durs)
        all_success_status_only += success_status_only
        all_success_ideal_results += success_ideal_results
        all_total += runs_count

    summary["totals"] = {
        "runs": len(all_ms),
        "avg_ms": round(statistics.mean(all_ms), 2) if all_ms else None,
        "p50_ms": round(percentile(all_ms, 50), 2) if all_ms else None,
        "p95_ms": round(percentile(all_ms, 95), 2) if all_ms else None,
        # Backward compatible total success_rate (status-only)
        "success_rate": round(all_success_status_only / max(1, all_total), 3) if all_total else None,
        "success_rate_status_only": round(all_success_status_only / max(1, all_total), 3) if all_total else None,
        "success_rate_ideal_results": round(all_success_ideal_results / max(1, all_total), 3) if all_total else None,
    }

    with summary_path.open("w", encoding="utf-8") as sf:
        json.dump(summary, sf, ensure_ascii=False, indent=2)

    print(f"[BENCH] Summary saved to {summary_path}")


if __name__ == "__main__":
    main()
