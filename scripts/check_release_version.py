"""Require one repository tag to match both independently published packages."""

from __future__ import annotations

import argparse
import pathlib
import tomllib

ROOT = pathlib.Path(__file__).resolve().parents[1]
PACKAGES = ("proofroot", "newlife")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("tag", help="release tag, for example v0.1.0")
    args = parser.parse_args()

    versions = {
        name: tomllib.loads(
            (ROOT / "packages" / name / "pyproject.toml").read_text(encoding="utf-8")
        )["project"]["version"]
        for name in PACKAGES
    }
    if len(set(versions.values())) != 1:
        raise SystemExit(f"package versions differ: {versions}")
    version = next(iter(versions.values()))
    if args.tag != f"v{version}":
        raise SystemExit(f"tag {args.tag!r} does not match package version {version!r}")
    print(f"release tag {args.tag} matches proofroot and newlife")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
