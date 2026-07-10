"""Metadata-only AUTHBOUND smoke for docs visibility and protected-route refusal."""

from __future__ import annotations

import argparse
import sys

import requests


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--docs-path", default="/docs")
    parser.add_argument("--protected-path", default="/metrics")
    parser.add_argument("--expect-unauthorized", action="store_true")
    args = parser.parse_args()

    docs_response = requests.get(f"{args.base_url.rstrip('/')}{args.docs_path}", timeout=10)
    if docs_response.status_code != 200:
        print(f"docs_status={docs_response.status_code}")
        return 1

    protected_response = requests.get(
        f"{args.base_url.rstrip('/')}{args.protected_path}",
        timeout=10,
    )
    if args.expect_unauthorized and protected_response.status_code not in (401, 403, 503):
        print(f"protected_status={protected_response.status_code}")
        return 1

    print(
        f"docs_status={docs_response.status_code} "
        f"protected_status={protected_response.status_code}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
