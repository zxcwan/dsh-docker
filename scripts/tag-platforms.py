#!/usr/bin/env python3
"""Give each platform manifest its own readable tag.

A multi-arch push only tags the index; the per-architecture manifests stay
untagged digests. This adds `<repo>:<version>-amd64` / `-arm64` pointing at them,
so the GHCR versions page shows named entries instead of bare sha256 hashes.

Usage: tag-platforms.py <repo-without-tag> <version>
"""

import json
import subprocess
import sys


def run(*cmd):
    return subprocess.run(cmd, check=True, capture_output=True, text=True).stdout


def main():
    repo, version = sys.argv[1], sys.argv[2]
    ref = f"{repo}:{version}"
    manifest = json.loads(run("docker", "buildx", "imagetools", "inspect", ref, "--format", "{{json .Manifest}}"))
    tagged = []
    for entry in manifest.get("manifests", []):
        platform = entry.get("platform") or {}
        if platform.get("os") != "linux":
            continue
        arch = platform.get("architecture")
        if arch not in ("amd64", "arm64"):
            continue
        tag = f"{repo}:{version}-{arch}"
        subprocess.run(["docker", "buildx", "imagetools", "create", "--tag", tag, f"{repo}@{entry['digest']}"], check=True, capture_output=True)
        tagged.append(tag)
        print(f"tagged {tag} -> {entry['digest']}")
    if not tagged:
        raise SystemExit("no linux/amd64 or linux/arm64 manifest found")


if __name__ == "__main__":
    main()
