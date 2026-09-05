"""Inspect built distributions for the files and metadata users depend on."""

from __future__ import annotations

import argparse
import email.parser
import pathlib
import tarfile
import zipfile

PACKAGES = ("proofroot", "newlife")


def _one(dist: pathlib.Path, pattern: str) -> pathlib.Path:
    matches = sorted(dist.glob(pattern))
    if len(matches) != 1:
        raise SystemExit(f"expected exactly one {pattern!r} in {dist}, found {matches}")
    return matches[0]


def _metadata(archive: zipfile.ZipFile) -> email.message.Message:
    names = [
        name for name in archive.namelist() if name.endswith(".dist-info/METADATA")
    ]
    if len(names) != 1:
        raise SystemExit(f"wheel has {len(names)} METADATA files, expected one")
    return email.parser.BytesParser().parsebytes(archive.read(names[0]))


def _require_suffix(names: set[str], suffix: str, label: str) -> None:
    if not any(name.endswith(suffix) for name in names):
        raise SystemExit(f"{label} is missing {suffix}")


def check_wheels(dist: pathlib.Path) -> None:
    proofroot = _one(dist, "proofroot-*.whl")
    newlife = _one(dist, "newlife-*.whl")

    with zipfile.ZipFile(proofroot) as archive:
        names = set(archive.namelist())
        _require_suffix(names, ".dist-info/licenses/LICENSE", proofroot.name)
        for vector in ("canonical_vectors.json", "evidencecore_rng_v1.json"):
            expected = f"proofroot/vectors/{vector}"
            if expected not in names:
                raise SystemExit(f"{proofroot.name} is missing {expected}")

    with zipfile.ZipFile(newlife) as archive:
        names = set(archive.namelist())
        _require_suffix(names, ".dist-info/licenses/LICENSE", newlife.name)
        for suffix in (
            "newlife/scaffold/prereg.sh",
            "newlife/scaffold/templates/goal.md",
            "newlife/scaffold/templates/next.md",
            "newlife/scaffold/templates/origin-README.md",
            "newlife/scaffold/templates/prereg.md",
            "newlife/scaffold/templates/verdict.py.template",
        ):
            _require_suffix(names, suffix, newlife.name)
        metadata = _metadata(archive)
        requirements = metadata.get_all("Requires-Dist", [])
        if not any(
            requirement.replace(" ", "").lower() == "proofroot<0.2,>=0.1"
            for requirement in requirements
        ):
            raise SystemExit(
                f"{newlife.name} does not declare the bounded proofroot dependency: "
                f"{requirements}"
            )
        entries = [
            name for name in names if name.endswith(".dist-info/entry_points.txt")
        ]
        if (
            len(entries) != 1
            or "newlife = newlife.cli:main" not in archive.read(entries[0]).decode()
        ):
            raise SystemExit(
                f"{newlife.name} does not expose the newlife console command"
            )


def check_sdists(dist: pathlib.Path) -> None:
    for package in PACKAGES:
        sdist = _one(dist, f"{package}-*.tar.gz")
        with tarfile.open(sdist, "r:gz") as archive:
            _require_suffix(set(archive.getnames()), "/LICENSE", sdist.name)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("dist", type=pathlib.Path)
    args = parser.parse_args()
    dist = args.dist.resolve()
    check_wheels(dist)
    check_sdists(dist)
    print(
        "release artifacts contain required licenses, assets, metadata, and CLI entry point"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
