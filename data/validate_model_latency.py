#!/usr/bin/env python3
"""Smoke-check and latency benchmark local Ollama models."""

from __future__ import annotations

import argparse
import json
import os
import statistics
import time
import urllib.error
import urllib.request
from pathlib import Path


DEFAULT_PROMPT = "Summarize settlement variance in one sentence."


def env(name: str, default: str) -> str:
    value = os.getenv(name, default).strip()
    return value or default


def request_json(url: str, payload: dict, timeout: int) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def ensure_non_empty_response(base_url: str, model: str, prompt: str, timeout: int) -> float:
    start = time.perf_counter()
    payload = {"model": model, "prompt": prompt, "stream": False}
    body = request_json(f"{base_url}/api/generate", payload, timeout)
    elapsed_ms = (time.perf_counter() - start) * 1000
    response_text = str(body.get("response", "")).strip()
    if not response_text:
        raise RuntimeError(f"Model '{model}' returned an empty response")
    return elapsed_ms


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    if len(sorted_values) == 1:
        return sorted_values[0]
    rank = (p / 100.0) * (len(sorted_values) - 1)
    lower = int(rank)
    upper = min(lower + 1, len(sorted_values) - 1)
    weight = rank - lower
    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


def benchmark_model(base_url: str, model: str, prompt: str, iterations: int, timeout: int) -> dict:
    latencies = [
        ensure_non_empty_response(base_url, model, prompt, timeout)
        for _ in range(iterations)
    ]
    return {
        "model": model,
        "iterations": iterations,
        "p50_ms": round(percentile(latencies, 50), 2),
        "p95_ms": round(percentile(latencies, 95), 2),
        "avg_ms": round(statistics.mean(latencies), 2),
        "max_ms": round(max(latencies), 2),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=env("OLLAMA_BASE_URL", "http://localhost:11434"))
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    parser.add_argument("--iterations", type=int, default=3)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument(
        "--models",
        nargs="*",
        default=[
            env("LOCAL_MODEL", "mistral"),
            env("ALTERNATE_LOCAL_MODEL", "gemma:2b"),
        ],
    )
    parser.add_argument("--output-json", default="data/generated/model_latency_report.json")
    args = parser.parse_args()

    if args.iterations < 1:
        raise ValueError("--iterations must be >= 1")

    output_path = Path(args.output_json)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    results: list[dict] = []
    for model in args.models:
        model = model.strip()
        if not model:
            continue
        try:
            results.append(
                benchmark_model(
                    args.base_url,
                    model,
                    args.prompt,
                    args.iterations,
                    args.timeout,
                )
            )
        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"Failed to reach Ollama at {args.base_url}. Start the service first."
            ) from exc

    if not results:
        raise RuntimeError("No models provided for latency validation")

    report = {
        "base_url": args.base_url,
        "prompt": args.prompt,
        "generated_at_epoch": int(time.time()),
        "results": results,
    }
    output_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print("Model latency report:")
    for row in results:
        print(
            f"- {row['model']}: p50={row['p50_ms']}ms p95={row['p95_ms']}ms "
            f"avg={row['avg_ms']}ms max={row['max_ms']}ms"
        )
    print(f"Saved report to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())