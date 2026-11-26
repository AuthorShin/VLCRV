#!/usr/bin/env bash
# Report outdated direct dependencies (uses only the Python standard library).
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

python3 - <<'PY'
import json
import re
import urllib.request

deps = []
for line in open("requirements.txt", encoding="utf-8"):
    match = re.match(r"^([A-Za-z0-9_.-]+)==([^\s]+)", line.strip())
    if match:
        deps.append(match.groups())

print(f"{'STATUS':9} {'PACKAGE':20} {'PINNED':12} LATEST")
for name, current in deps:
    try:
        with urllib.request.urlopen(
            f"https://pypi.org/pypi/{name}/json", timeout=10
        ) as response:
            latest = json.load(response)["info"]["version"]
        status = "OK" if latest == current else "OUTDATED"
    except Exception as exc:
        latest, status = f"error: {exc}", "UNKNOWN"
    print(f"{status:9} {name:20} {current:12} {latest}")
PY

echo
echo "To update:"
echo "  1. Edit requirements.txt with the new version(s)."
echo "  2. pip install -r requirements.txt -r requirements-dev.txt"
echo "  3. python tests/smoke_test.py"
echo "  4. docker compose up -d --build"
echo
echo "For a fully reproducible tree (including transitive deps):"
echo "  pip-compile -o requirements.lock.txt requirements.txt"
