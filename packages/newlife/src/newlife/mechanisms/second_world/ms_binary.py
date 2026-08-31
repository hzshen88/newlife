"""Build-and-run helpers for the vendored `ms` reference oracle (R1): the
exact compile command, subprocess invocation, and stdout parser — a single
source of truth for "what does a real, fresh `ms` run look like", shared
by the test suite and the verdict runner (Task 3) rather than duplicated
per caller.
"""

from __future__ import annotations

import subprocess
from pathlib import Path


def build_ms(vendor_root: Path, output_path: Path) -> Path:
    """R1's exact reference build command, substituting the instrumented
    `rand1.c` for draw logging (verified byte-identical stdout to the
    pristine build when `MS_DRAW_LOG` is unset)."""
    cmd = [
        "cc",
        "-O2",
        "-ffp-contract=off",
        "-std=gnu89",
        "-Wno-error=implicit-function-declaration",
        "-Wno-error=implicit-int",
        "-Wno-error=return-type",
        str(vendor_root / "ms.c"),
        str(vendor_root / "streec.c"),
        str(vendor_root / "verification" / "rand1_instrumented.c"),
        "-o",
        str(output_path),
        "-lm",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ms build failed:\n{result.stderr}")
    return output_path


def run_ms(
    ms_binary: Path,
    nsam: int,
    howmany: int,
    theta: float,
    seeds: tuple[int, int, int],
    draw_log: Path,
) -> str:
    cmd = [
        str(ms_binary),
        str(nsam),
        str(howmany),
        "-t",
        str(theta),
        "-seeds",
        str(seeds[0]),
        str(seeds[1]),
        str(seeds[2]),
    ]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env={"MS_DRAW_LOG": str(draw_log), "PATH": "/usr/bin:/bin"},
    )
    if result.returncode != 0:
        raise RuntimeError(f"ms run failed:\n{result.stderr}")
    return result.stdout


def parse_ms_stdout(
    stdout: str, nsam: int, howmany: int
) -> list[tuple[int, list[str]]]:
    """Parses `howmany` "//"-delimited replicate blocks (ms.c:177-193):
    "segsites: N", then (only if N>0) a "positions:" line followed by N
    genotype rows — a "segsites==0" replicate prints neither (R3)."""
    lines = stdout.split("\n")
    replicates: list[tuple[int, list[str]]] = []
    i = 0
    while i < len(lines) and len(replicates) < howmany:
        if lines[i].strip() == "//" or lines[i].startswith("//"):
            i += 1
            if not lines[i].startswith("segsites: "):
                raise ValueError(f"expected 'segsites: ' line, got: {lines[i]!r}")
            segsites = int(lines[i].removeprefix("segsites: "))
            i += 1
            if segsites > 0:
                if not lines[i].startswith("positions: "):
                    raise ValueError(f"expected 'positions: ' line, got: {lines[i]!r}")
                i += 1
                rows = [lines[i + k] for k in range(nsam)]
                i += nsam
            else:
                # the unconditional trailing "\n" after the (skipped)
                # positions loop (ms.c:188-191) — a blank line, no rows.
                i += 1
                rows = []
            replicates.append((segsites, rows))
        else:
            i += 1
    if len(replicates) != howmany:
        raise ValueError(f"expected {howmany} replicates, parsed {len(replicates)}")
    return replicates
