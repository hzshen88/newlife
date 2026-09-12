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
            "newlife/skills/newlife/SKILL.md",
            "newlife/skills/newlife/references/workflow-contract.md",
            "newlife/skills/newlife/references/method-provenance.md",
            "newlife/skills/newlife-execute/SKILL.md",
            "newlife/skills/newlife-execute/references/anomaly-and-verification.md",
            "newlife/skills/newlife-execute/references/review-and-closeout.md",
            "newlife/skills/newlife-goal/SKILL.md",
            "newlife/skills/newlife-goal/references/evidence.md",
            "newlife/skills/newlife-prereg/SKILL.md",
            "newlife/skills/newlife-prereg/references/analysis-design.md",
            "newlife/skills/newlife-prereg/references/cases.md",
            "newlife/skills/newlife-prereg/references/design.md",
        ):
            _require_suffix(names, suffix, newlife.name)
        _require_suffix(
            names,
            ".dist-info/licenses/THIRD_PARTY_NOTICES.md",
            newlife.name,
        )
        metadata = _metadata(archive)
        requirements = metadata.get_all("Requires-Dist", [])
        # Stated here by hand on purpose: reading the range back out of pyproject.toml
        # would make this true by construction and check nothing. Moving a range means
        # editing this line too — docs/releasing.md step 2 says so, because forgetting it
        # is how a bump first shows up as a failed build.
        for dependency in ("proofroot<0.2,>=0.1", "exloop<0.4,>=0.3"):
            if not any(
                requirement.replace(" ", "").lower() == dependency
                for requirement in requirements
            ):
                raise SystemExit(
                    f"{newlife.name} does not declare the bounded dependency "
                    f"{dependency}: {requirements}"
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
        active = "\n".join(
            archive.read(name).decode("utf-8")
            for name in names
            if "/skills/" in name and name.endswith(".md")
        )
        if "science-superpowers:" in active:
            raise SystemExit(
                f"{newlife.name} contains an active Science-Superpowers invocation"
            )


def check_sdists(dist: pathlib.Path) -> None:
    for package in PACKAGES:
        sdist = _one(dist, f"{package}-*.tar.gz")
        with tarfile.open(sdist, "r:gz") as archive:
            names = set(archive.getnames())
            _require_suffix(names, "/LICENSE", sdist.name)
            if package == "newlife":
                _require_suffix(names, "/THIRD_PARTY_NOTICES.md", sdist.name)


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
