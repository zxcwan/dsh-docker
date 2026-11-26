#!/usr/bin/env python3
"""Resolve which dsh versions the image build should produce.

Reads the npm packument and the GitHub releases list, keeps versions that are
released *and* published to npm (npm publishing lags release tags), and prints
two lines:

  line 1: newest installable version (may be an alpha)
  line 2: newest non-alpha version (rc or stable) — the one that moves `latest`

The ordering is real semver, not `sort -V`: a release sorts after its own
prereleases (0.2.2 > 0.2.2-rc.10) and numeric prerelease identifiers compare
numerically (rc.10 > rc.5).

Usage: dsh-versions.py <packument.json> <releases.json>
"""

import json
import re
import sys


def prerelease_key(prerelease):
    return [(0, int(part)) if part.isdigit() else (1, part) for part in prerelease.split(".")]


def version_key(version):
    base, _, prerelease = version.partition("-")
    numbers = tuple(int(part) for part in base.split("."))
    return (numbers, 0 if not prerelease else 1, prerelease_key(prerelease))


def main():
    packument_path, releases_path = sys.argv[1], sys.argv[2]
    with open(packument_path, encoding="utf-8") as handle:
        published = set(json.load(handle).get("versions", {}))
    with open(releases_path, encoding="utf-8") as handle:
        releases = json.load(handle)

    candidates = set()
    for release in releases:
        name = re.sub(r"^v", "", str(release.get("name") or release.get("tag_name") or ""))
        if not re.match(r"^\d+\.\d+\.\d+$", name.split("-")[0]):
            continue
        if name not in published:
            continue
        candidates.add(name)

    ordered = sorted(candidates, key=version_key)
    newest = ordered[-1] if ordered else ""
    stable = [version for version in ordered if "-alpha" not in version.lower()]
    stable_newest = stable[-1] if stable else ""
    print(newest)
    print(stable_newest)


if __name__ == "__main__":
    main()