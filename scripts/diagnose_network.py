#!/usr/bin/env python3
"""Cross-platform development endpoint reachability probe.

This script is intentionally read-only. It does not modify local configuration.

Examples:
  python scripts/diagnose_network.py --profile ai --timeout 5
  python scripts/diagnose_network.py --profile python --json
  python scripts/diagnose_network.py --url https://pypi.tuna.tsinghua.edu.cn/simple
"""
from __future__ import annotations

import argparse
import json
import socket
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from typing import Iterable

PROFILES = {
    "python": [
        "https://pypi.org/simple",
        "https://pypi.tuna.tsinghua.edu.cn/simple",
        "https://mirrors.ustc.edu.cn/pypi/simple",
        "https://mirrors.aliyun.com/pypi/simple/",
        "https://repo.huaweicloud.com/repository/pypi/simple",
    ],
    "node": [
        "https://registry.npmjs.org/",
        "https://registry.npmmirror.com/",
        "https://mirrors.tencent.com/npm/",
        "https://repo.huaweicloud.com/repository/npm/",
    ],
    "docker": [
        "https://registry-1.docker.io/v2/",
        "https://docker.m.daocloud.io/v2/",
        "https://docker.1ms.run/v2/",
        "https://docker.xuanyuan.me/v2/",
        "https://dockerproxy.net/v2/",
    ],
    "git": [
        "https://github.com/",
        "https://objects.githubusercontent.com/",
        "https://release-assets.githubusercontent.com/",
    ],
    "ai": [
        "https://huggingface.co/",
        "https://hf-mirror.com/",
        "https://www.modelscope.cn/",
        "https://pypi.tuna.tsinghua.edu.cn/simple",
        "https://registry.npmmirror.com/",
    ],
    "os": [
        "https://mirrors.tuna.tsinghua.edu.cn/",
        "https://mirrors.ustc.edu.cn/",
        "https://mirrors.bfsu.edu.cn/",
        "https://mirrors.aliyun.com/",
        "https://repo.huaweicloud.com/",
    ],
    "browser": [
        "https://playwright.azureedge.net/",
        "https://storage.googleapis.com/",
        "https://msedge.sf.dl.delivery.mp.microsoft.com/",
    ],
}

REACHABLE_HTTP_CODES = {200, 204, 301, 302, 307, 308, 401, 403, 404, 405}


@dataclass
class ProbeResult:
    url: str
    ok: bool
    status: int | None
    elapsed_ms: int | None
    error: str | None
    reachable: bool


def probe(url: str, timeout: float) -> ProbeResult:
    start = time.perf_counter()
    request = urllib.request.Request(url, method="GET", headers={"User-Agent": "china-dev-network-probe/1.0"})
    try:
        context = ssl.create_default_context()
        with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
            response.read(256)
            elapsed = int((time.perf_counter() - start) * 1000)
            status = getattr(response, "status", None)
            return ProbeResult(url=url, ok=True, status=status, elapsed_ms=elapsed, error=None, reachable=True)
    except urllib.error.HTTPError as exc:
        elapsed = int((time.perf_counter() - start) * 1000)
        reachable = exc.code in REACHABLE_HTTP_CODES
        error = None if reachable else f"HTTPError: {exc.code} {exc.reason}"
        return ProbeResult(url=url, ok=reachable, status=exc.code, elapsed_ms=elapsed, error=error, reachable=True)
    except Exception as exc:  # noqa: BLE001 - diagnostics should report any error type
        elapsed = int((time.perf_counter() - start) * 1000)
        return ProbeResult(url=url, ok=False, status=getattr(exc, "code", None), elapsed_ms=elapsed, error=f"{type(exc).__name__}: {exc}", reachable=False)


def dns_probe(host: str, timeout: float) -> dict[str, object]:
    old_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(timeout)
    start = time.perf_counter()
    try:
        infos = socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)
        elapsed = int((time.perf_counter() - start) * 1000)
        addresses = sorted({item[4][0] for item in infos})
        return {"host": host, "ok": True, "elapsed_ms": elapsed, "addresses": addresses[:8], "error": None}
    except Exception as exc:  # noqa: BLE001
        elapsed = int((time.perf_counter() - start) * 1000)
        return {"host": host, "ok": False, "elapsed_ms": elapsed, "addresses": [], "error": f"{type(exc).__name__}: {exc}"}
    finally:
        socket.setdefaulttimeout(old_timeout)


def unique_urls(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            output.append(value)
    return output


def build_summary(results: list[ProbeResult]) -> dict[str, object]:
    successes = [result for result in results if result.ok]
    failures = [result for result in results if not result.ok]
    fastest = min(successes, key=lambda result: result.elapsed_ms or 10**9) if successes else None
    return {
        "total": len(results),
        "ok_count": len(successes),
        "failed_count": len(failures),
        "fastest_ok_url": fastest.url if fastest else None,
        "fastest_ok_elapsed_ms": fastest.elapsed_ms if fastest else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe common mainland-China developer endpoints.")
    parser.add_argument("--profile", choices=sorted(PROFILES), action="append", help="Endpoint profile to test. Can be repeated.")
    parser.add_argument("--url", action="append", default=[], help="Extra URL to test. Can be repeated.")
    parser.add_argument("--timeout", type=float, default=5.0, help="Per-endpoint timeout in seconds. Default: 5")
    parser.add_argument("--dns", action="store_true", help="Also probe DNS for URL hosts.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a human-readable table.")
    args = parser.parse_args()

    profiles = args.profile or ["python", "node", "docker", "ai"]
    urls: list[str] = []
    for profile in profiles:
        urls.extend(PROFILES[profile])
    urls.extend(args.url)
    urls = unique_urls(urls)

    results = [probe(url, args.timeout) for url in urls]
    dns_results: list[dict[str, object]] = []
    if args.dns:
        hosts = unique_urls([(urllib.parse.urlparse(url).hostname or url) for url in urls])
        dns_results = [dns_probe(host, args.timeout) for host in hosts]

    payload = {"profiles": profiles, "results": [asdict(result) for result in results], "dns": dns_results, "summary": build_summary(results)}

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"{'OK':<4} {'MS':>6} {'STATUS':>7} URL")
        for result in sorted(results, key=lambda item: (not item.ok, item.elapsed_ms or 10**9, item.url)):
            ok = "yes" if result.ok else "no"
            ms = str(result.elapsed_ms) if result.elapsed_ms is not None else "-"
            status = str(result.status) if result.status is not None else "-"
            print(f"{ok:<4} {ms:>6} {status:>7} {result.url}")
            if not result.ok and result.error:
                print(f"     error: {result.error}")
        print("\nSummary")
        summary = payload["summary"]
        print(f"ok: {summary['ok_count']}/{summary['total']}")
        if summary["fastest_ok_url"]:
            print(f"fastest_ok: {summary['fastest_ok_url']} ({summary['fastest_ok_elapsed_ms']} ms)")
        if dns_results:
            print("\nDNS")
            for item in dns_results:
                print(json.dumps(item, ensure_ascii=False, sort_keys=True))

    return 0 if any(result.ok for result in results) else 2


if __name__ == "__main__":
    sys.exit(main())
