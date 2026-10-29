
from __future__ import annotations

import asyncio
import json
import os
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

BASE_URL = os.getenv("HMS_BASE_URL", "http://127.0.0.1:8000")
USERNAME = os.getenv("HMS_LOAD_USERNAME", "warden")
PASSWORD = os.getenv("HMS_LOAD_PASSWORD")
CONCURRENT_USERS = 50
REQUESTS_PER_USER = 10
TIMEOUT_SECONDS = 10

RESULTS_DIR = Path("tests/performance/results")


async def main() -> None:
    if not PASSWORD:
        raise SystemExit(
            "Set HMS_LOAD_PASSWORD to the password of an existing "
            "administrator account before running this test."
        )

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    latencies: list[float] = []
    failures: list[str] = []
    completed_under_two_seconds = 0
    successful_requests = 0

    limits = httpx.Limits(
        max_connections=CONCURRENT_USERS,
        max_keepalive_connections=CONCURRENT_USERS,
    )
    timeout = httpx.Timeout(TIMEOUT_SECONDS)

    async with httpx.AsyncClient(
        base_url=BASE_URL,
        timeout=timeout,
        limits=limits,
    ) as client:
        # Authenticate once for each simulated user.
        login_tasks = [
            client.post(
                "/api/v1/auth/login",
                json={"identifier": USERNAME, "password": PASSWORD},
            )
            for _ in range(CONCURRENT_USERS)
        ]
        login_responses = await asyncio.gather(
            *login_tasks, return_exceptions=True
        )

        tokens: list[str] = []
        for index, response in enumerate(login_responses):
            if isinstance(response, Exception):
                failures.append(f"login user {index + 1}: {response}")
            elif response.status_code != 200:
                failures.append(
                    f"login user {index + 1}: HTTP {response.status_code}"
                )
            else:
                tokens.append(response.json()["access_token"])

        if not tokens:
            raise SystemExit(
                "No simulated users could authenticate. Check the server, "
                "credentials, and database."
            )

        # Exercise authenticated read endpoints. Each simulated user has
        # its own token, and all users share the HTTP connection pool.
        endpoints = ["/api/v1/rooms", "/api/v1/students", "/api/v1/allocations"]

        async def read_request(user_index: int, request_index: int) -> None:
            nonlocal successful_requests, completed_under_two_seconds

            token = tokens[user_index % len(tokens)]
            endpoint = endpoints[request_index % len(endpoints)]
            started = time.perf_counter()

            try:
                response = await client.get(
                    endpoint,
                    headers={"Authorization": f"Bearer {token}"},
                )
                elapsed = time.perf_counter() - started
                latencies.append(elapsed)

                if response.status_code == 200:
                    successful_requests += 1
                    if elapsed < 2.0:
                        completed_under_two_seconds += 1
                else:
                    failures.append(
                        f"{endpoint}: HTTP {response.status_code}"
                    )
            except Exception as exc:
                elapsed = time.perf_counter() - started
                latencies.append(elapsed)
                failures.append(f"{endpoint}: {type(exc).__name__}: {exc}")

        started_at = datetime.now(timezone.utc).isoformat()
        test_started = time.perf_counter()

        async def simulate_user(user_index: int) -> None:
            for request_index in range(REQUESTS_PER_USER):
                await read_request(user_index, request_index)

        await asyncio.gather(
            *(simulate_user(user_index) for user_index in range(len(tokens)))
        )

        duration = time.perf_counter() - test_started

    total_requests = len(latencies)
    within_target_percent = (
        100 * completed_under_two_seconds / total_requests
        if total_requests
        else 0.0
    )
    sorted_latencies = sorted(latencies)

    def percentile(values: list[float], p: float) -> float:
        if not values:
            return 0.0
        index = min(int((p / 100) * len(values)), len(values) - 1)
        return values[index] * 1000

    report = {
        "started_at_utc": started_at,
        "base_url": BASE_URL,
        "configured_concurrent_users": CONCURRENT_USERS,
        "authenticated_users": len(tokens),
        "requests_per_user": REQUESTS_PER_USER,
        "read_requests_attempted": total_requests,
        "successful_read_requests": successful_requests,
        "failed_requests": len(failures),
        "duration_seconds": round(duration, 3),
        "requests_per_second": round(total_requests / duration, 2)
        if duration
        else 0,
        "average_latency_ms": round(statistics.mean(latencies) * 1000, 2)
        if latencies
        else 0,
        "p95_latency_ms": round(percentile(sorted_latencies, 95), 2),
        "requests_under_2_seconds_percent": round(
            within_target_percent, 2
        ),
        "target_met": within_target_percent >= 95.0
        and len(tokens) == CONCURRENT_USERS
        and not failures,
        "failure_samples": failures[:20],
        "note": (
            "Local development measurement only. Results depend on the "
            "machine, server configuration, SQLite database, and dataset."
        ),
    }

    result_path = RESULTS_DIR / "latest.json"
    result_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(json.dumps(report, indent=2))
    print(f"\nSaved results to: {result_path}")


if __name__ == "__main__":
    asyncio.run(main())
