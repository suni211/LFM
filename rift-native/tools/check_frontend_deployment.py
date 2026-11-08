"""Check which frontend bytes the GCP test backend and 18771 proxy serve.

Run on GCP after pulling the feature branch:
    python3 rift-native/tools/check_frontend_deployment.py

Read-only: no databases, processes or files are modified.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
TEST_FRONT = "http://127.0.0.1:18771/rift"
TEST_API = "http://127.0.0.1:18770"
BUILD = str(int(time.time() * 1000))


def fetch(url: str) -> tuple[int, bytes]:
    try:
        with urlopen(url, timeout=5) as response:
            return response.status, response.read()
    except HTTPError as error:
        return error.code, error.read()
    except (URLError, TimeoutError, OSError) as error:
        raise RuntimeError(f"{url}: {error}") from error


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:16]


def main() -> int:
    failures = []
    for filename in ("index.html", "app.js", "app.css"):
        disk = ROOT / "web" / filename
        expected = disk.read_bytes()
        suffix = "/" if filename == "index.html" else "/static/" + filename
        proxy_suffix = "/" if filename == "index.html" else "/static/" + filename
        upstream = TEST_API + suffix + "?verify=" + BUILD
        public = TEST_FRONT + proxy_suffix + "?verify=" + BUILD
        print(f"\n{filename}: checkout SHA256 {digest(expected)}")
        for name, url in (("backend 18770", upstream), ("frontend 18771", public)):
            try:
                status, actual = fetch(url)
            except RuntimeError as error:
                failures.append(str(error))
                print(f"  {name}: unreachable ({error})")
                continue
            html = actual.lstrip().lower().startswith((b"<!doctype html", b"<html"))
            matches = (status == 200 and actual == expected)
            print(f"  {name}: HTTP {status}; SHA256 {digest(actual)}; "
                  f"{'MATCH' if matches else 'MISMATCH'}"
                  f"{' (HTML returned for CSS/JS)' if html and filename != 'index.html' else ''}")
            if not matches:
                failures.append(f"{name} serves a different {filename}")
    print("\n/health revision and hashes:")
    for name, url in (
        ("backend", TEST_API + "/health"),
        ("frontend proxy", TEST_FRONT + "/api/health")
    ):
        try:
            status, response = fetch(url)
            if status != 200:
                failures.append(f"{name} health HTTP {status}")
                print(f"  {name}: HTTP {status}")
                continue
            data = json.loads(response)
            print(f"  {name}: revision={data.get('revision')}; "
                  f"web_sha256={data.get('web_sha256')}")
        except (ValueError, RuntimeError) as error:
            failures.append(f"{name} health: {error}")
            print(f"  {name}: {error}")
    if failures:
        print("\nCHECK FAILED:")
        for failure in failures:
            print(" -", failure)
        print("Confirm the running 18770 Python process and the 18771 proxy "
              "serve ~/LFM-test/rift-native/web/ rather than an older checkout.")
        return 1
    print("\nPASS: on-disk checkout, backend and frontend proxy match exactly.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
