"""Benchmark latency for the primary strategy analysis endpoint."""

from __future__ import annotations

import argparse
import os
import socket
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import TextIO
from typing import Sequence
from urllib.parse import urlencode

import httpx

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DRIVER = "VER"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_RACE_ID = "2024_monza_race"
DEFAULT_RUNS = 20
HEALTH_PATH = "/health"
HEALTH_TIMEOUT_SECONDS = 15.0
REQUEST_TIMEOUT_SECONDS = 180.0


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the benchmark script."""
    parser = argparse.ArgumentParser(
        description=(
            "Benchmark the strategy endpoint before and after caching."
        ),
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=DEFAULT_RUNS,
        help=(
            "Measured runs per mode. "
            "Must be between 20 and 30."
        ),
    )
    parser.add_argument(
        "--race-id",
        default=DEFAULT_RACE_ID,
        help="Race identifier to benchmark.",
    )
    parser.add_argument(
        "--driver",
        default=DEFAULT_DRIVER,
        help="Three-letter driver code.",
    )
    parser.add_argument(
        "--host",
        default=DEFAULT_HOST,
        help="Host for the managed local benchmark server.",
    )
    return parser.parse_args()


def validate_runs(runs: int) -> int:
    """Validate the configured measured run count."""
    if 20 <= runs <= 30:
        return runs
    raise ValueError("runs must be between 20 and 30")


def build_endpoint_path(race_id: str, driver_code: str) -> str:
    """Build the cache-friendly strategy endpoint path."""
    query = urlencode({"driver": driver_code.strip().upper()})
    return f"/race/{race_id}/strategy?{query}"


def compute_median(latencies_ms: Sequence[float]) -> float:
    """Return the median latency in milliseconds."""
    return float(statistics.median(latencies_ms))


def compute_average(latencies_ms: Sequence[float]) -> float:
    """Return the mean latency in milliseconds."""
    return float(statistics.fmean(latencies_ms))


def compute_percent_reduction(
    before_ms: float,
    after_ms: float,
) -> float | None:
    """Return the percentage latency reduction from before to after."""
    if before_ms == 0:
        return None
    return ((before_ms - after_ms) / before_ms) * 100.0


def choose_free_port(host: str) -> int:
    """Return an available TCP port on the requested host."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return int(sock.getsockname()[1])


def build_database_url(db_path: Path) -> str:
    """Return a SQLite database URL for a temporary benchmark DB."""
    return f"sqlite:///{db_path}"


class BenchmarkServer:
    """Manage a temporary uvicorn process for benchmark requests."""

    def __init__(self, host: str, database_url: str, log_path: Path) -> None:
        self.host = host
        self.port = choose_free_port(host)
        self.base_url = f"http://{host}:{self.port}"
        self.database_url = database_url
        self.log_path = log_path
        self.process: subprocess.Popen[str] | None = None
        self._log_handle: TextIO | None = None

    def start(self) -> None:
        """Start the uvicorn subprocess and wait for readiness."""
        env = os.environ.copy()
        env["DATABASE_URL"] = self.database_url
        env["PYTHONUNBUFFERED"] = "1"

        command = [
            sys.executable,
            "-m",
            "uvicorn",
            "backend.app.main:app",
            "--host",
            self.host,
            "--port",
            str(self.port),
        ]

        self._log_handle = self.log_path.open("w", encoding="utf-8")
        self.process = subprocess.Popen(
            command,
            cwd=PROJECT_ROOT,
            env=env,
            stdout=self._log_handle,
            stderr=subprocess.STDOUT,
            text=True,
        )

        self.wait_until_ready()

    def wait_until_ready(self) -> None:
        """Wait until the managed server responds to the health check."""
        deadline = time.monotonic() + HEALTH_TIMEOUT_SECONDS
        health_url = f"{self.base_url}{HEALTH_PATH}"

        while time.monotonic() < deadline:
            if self.process is None:
                raise RuntimeError("server process was not started")

            if self.process.poll() is not None:
                raise RuntimeError(
                    "benchmark server exited during startup\n"
                    f"{self.read_logs()}"
                )

            try:
                response = httpx.get(
                    health_url,
                    timeout=1.0,
                )
            except httpx.HTTPError:
                time.sleep(0.2)
                continue

            if response.status_code == 200:
                return

            time.sleep(0.2)

        raise RuntimeError(
            "benchmark server did not become ready in time\n"
            f"{self.read_logs()}"
        )

    def stop(self) -> None:
        """Stop the managed uvicorn process."""
        if self.process is not None and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5.0)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5.0)

        if self._log_handle is not None:
            self._log_handle.close()
            self._log_handle = None

    def read_logs(self) -> str:
        """Return collected server logs for debugging failures."""
        if self._log_handle is not None:
            self._log_handle.flush()
        if not self.log_path.exists():
            return ""
        return self.log_path.read_text(encoding="utf-8")

    def __enter__(self) -> "BenchmarkServer":
        """Start the benchmark server for a context manager block."""
        self.start()
        return self

    def __exit__(self, *args: object) -> None:
        """Stop the benchmark server when the context exits."""
        self.stop()


def time_request(base_url: str, endpoint_path: str) -> float:
    """Time one HTTP GET request and return latency in milliseconds."""
    request_url = f"{base_url}{endpoint_path}"
    started_at = time.perf_counter()
    response = httpx.get(request_url, timeout=REQUEST_TIMEOUT_SECONDS)
    elapsed_ms = (time.perf_counter() - started_at) * 1000.0
    response.raise_for_status()
    return elapsed_ms


def run_cold_benchmark(
    runs: int,
    host: str,
    endpoint_path: str,
) -> list[float]:
    """Measure cold latency with a fresh DB and process for each run."""
    latencies_ms: list[float] = []

    for run_index in range(1, runs + 1):
        with tempfile.TemporaryDirectory(
            prefix=f"f1-bench-cold-{run_index:02d}-"
        ) as temp_dir:
            temp_path = Path(temp_dir)
            db_path = temp_path / "benchmark.sqlite"
            log_path = temp_path / "uvicorn.log"
            database_url = build_database_url(db_path)

            with BenchmarkServer(host, database_url, log_path) as server:
                latency_ms = time_request(server.base_url, endpoint_path)

            latencies_ms.append(latency_ms)

    return latencies_ms


def run_warm_benchmark(
    runs: int,
    host: str,
    endpoint_path: str,
) -> tuple[float, list[float]]:
    """Measure warm latency after one cache-priming request."""
    with tempfile.TemporaryDirectory(prefix="f1-bench-warm-") as temp_dir:
        temp_path = Path(temp_dir)
        db_path = temp_path / "benchmark.sqlite"
        log_path = temp_path / "uvicorn.log"
        database_url = build_database_url(db_path)

        with BenchmarkServer(host, database_url, log_path) as server:
            warmup_ms = time_request(server.base_url, endpoint_path)
            latencies_ms = [
                time_request(server.base_url, endpoint_path)
                for _ in range(runs)
            ]

    return warmup_ms, latencies_ms


def format_latency(value_ms: float) -> str:
    """Return a consistent latency string."""
    return f"{value_ms:.2f} ms"


def format_percent(value: float | None) -> str:
    """Return a consistent percentage string."""
    if value is None:
        return "n/a"
    return f"{value:.2f}%"


def main() -> int:
    """Run the latency benchmark and print the summary."""
    args = parse_args()

    try:
        runs = validate_runs(args.runs)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    endpoint_path = build_endpoint_path(args.race_id, args.driver)

    try:
        cold_latencies_ms = run_cold_benchmark(
            runs=runs,
            host=args.host,
            endpoint_path=endpoint_path,
        )
        warmup_ms, warm_latencies_ms = run_warm_benchmark(
            runs=runs,
            host=args.host,
            endpoint_path=endpoint_path,
        )
    except (httpx.HTTPError, RuntimeError) as exc:
        print(f"Benchmark failed: {exc}", file=sys.stderr)
        return 1

    median_before_ms = compute_median(cold_latencies_ms)
    median_after_ms = compute_median(warm_latencies_ms)
    average_before_ms = compute_average(cold_latencies_ms)
    average_after_ms = compute_average(warm_latencies_ms)
    improvement = compute_percent_reduction(
        median_before_ms,
        median_after_ms,
    )

    print(f"endpoint tested: {endpoint_path}")
    print(f"number of runs: {runs}")
    print(
        "before mode: cold app state per run "
        "(fresh process, fresh SQLite persistence)"
    )
    print(
        "after mode: warm app state "
        "(shared process and persistence after one warm-up request)"
    )
    print(
        "limitation: FastF1 disk cache under cache/ may already be warm, so "
        "the 'before' numbers isolate app persistence and in-memory caching "
        "rather than a full upstream-download cold start."
    )
    print(f"warm-up latency after: {format_latency(warmup_ms)}")
    print(f"median latency before: {format_latency(median_before_ms)}")
    print(f"median latency after: {format_latency(median_after_ms)}")
    print(f"average latency before: {format_latency(average_before_ms)}")
    print(f"average latency after: {format_latency(average_after_ms)}")
    print(f"percent improvement: {format_percent(improvement)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
