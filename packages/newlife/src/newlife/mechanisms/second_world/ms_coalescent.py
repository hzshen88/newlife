"""Standalone, dependency-free port of Hudson's `ms` minimal-model algorithm
(preregistration R3: single population, `r=f=alphag=0`, `-t theta` infinite
sites). Replays a real `ms` binary's own logged `drand48()` draws in the
exact call order the C source makes them — never a hand-derived draw count.

Traced against `vendor/ms/{ms.c,streec.c}` (`segtre_mig`/`ca`/`pick2`/
`gensam`/`make_gametes`/`poisso`/`pickb`/`tdesn`), not merely against the
analysis plan's prose. Source citations are in each function's docstring.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

# `ms`'s getpars() default when -r is never supplied; fixed for this
# minimal model (recombination, which is what varies nsites, is out of
# scope per R3).
NSITES = 2


class DrawExhausted(RuntimeError):
    """A replicate needed a draw the recorded stream did not have."""


class UnsupportedGasdevBranch(NotImplementedError):
    """`poisso(u)`'s `u > 30` branch (`gasdev`'s Box-Muller state) is out of
    scope per R3/0.4 — raised rather than silently approximated."""

    def __init__(self, u: float) -> None:
        super().__init__(f"poisso(u={u!r}) exceeds the u<=30 scope boundary (R3)")
        self.u = u


class RecordedDrawStream:
    """Replays a fixed sequence of `ran1()` draws, in order, raising loudly
    on exhaustion rather than silently returning a wrong value (R4)."""

    def __init__(self, values: list[float]) -> None:
        self._values = values
        self._index = 0

    @classmethod
    def from_log_file(cls, path) -> "RecordedDrawStream":
        with open(path) as f:
            return cls([float(line) for line in f if line.strip()])

    def next(self) -> float:
        if self._index >= len(self._values):
            raise DrawExhausted(
                f"draw stream exhausted after {self._index} of {len(self._values)} draws"
            )
        value = self._values[self._index]
        self._index += 1
        return value

    @property
    def consumed(self) -> int:
        return self._index

    @property
    def leftover(self) -> int:
        return len(self._values) - self._index


@dataclass
class ReplicateResult:
    segsites: int
    genotype_rows: list[str]  # one string per sample, in mutation-placement order


def _build_coalescent_tree(
    nsam: int, draws: RecordedDrawStream
) -> tuple[list[float], list[int]]:
    """The `while(nchrom>1)` loop of `segtre_mig` (streec.c), specialized to
    the case every lineage always "has" the sole segment (no recombination,
    so `nsegs` stays 1 for the whole run and `ca()`'s multi-segment
    bookkeeping never applies).

    `size[pop]=1.0`, `alphag[pop]=0` fixed (R3) reduce the coalescent-timing
    draw (streec.c:212-214) to `ttemp = -log(rdum)/(n*(n-1))`; `prect=0` and
    `mig=0` (no recombination, no migration/pop structure) mean the 'r' and
    'm' event branches are never reachable, and `nextevent` is always NULL
    (no demographic events), so every iteration executes the 'c' branch
    (streec.c:375-380): `pick2_chrom` -> `ca`.

    Returns `(time, abv)`, each of length `2*nsam-1` (tips `0..nsam-1`,
    internal nodes `nsam..2*nsam-2`; the root's own `abv` entry is never
    read by `ttime`/`pickb`/`tdesn`, matching `ms`'s zero-initialized,
    never-assigned array slot for it).
    """
    n_nodes = 2 * nsam - 1
    time = [0.0] * n_nodes
    abv = [0] * n_nodes
    # `active[i]` is the tree-node index chromosome slot `i` currently
    # represents — the Python equivalent of `chrom[i].pseg->desc` (ca.c).
    active = list(range(nsam))
    t = 0.0
    next_node = nsam  # nnodes[0] starts at nsam-1; first assigned id is nsam

    while len(active) > 1:
        n = len(active)

        # streec.c:212-214 (coal_prob = n*(n-1), alphag==0 branch)
        rdum = draws.next()
        while rdum == 0.0:  # streec.c:212's retry-on-exactly-0.0 guard
            rdum = draws.next()
        t += -math.log(rdum) / (n * (n - 1))

        # ms.c:952-960 pick2(n,&i,&j): C double->int truncation, retry
        # while the truncated j equals the truncated i.
        i = int(n * draws.next())
        j = int(n * draws.next())
        while j == i:
            j = int(n * draws.next())
        c1, c2 = (i, j) if i < j else (j, i)  # streec.c:685-686 pick2_chrom sort

        # ca()'s single-segment merge (streec.c:606-616): both children's
        # abv point to the new node, whose time is set unconditionally
        # regardless of the tseg<0 "fully absorbed" branch that fires on
        # the final merge (that branch only changes chrom[]/nchrom
        # bookkeeping, never the abv/time arrays — see the plan's round-2
        # note on this).
        new_node = next_node
        next_node += 1
        abv[active[c1]] = new_node
        abv[active[c2]] = new_node
        time[new_node] = t

        # streec.c:648-651 swap-with-last chromosome bookkeeping.
        active[c1] = new_node
        active[c2] = active[-1]
        active.pop()

    return time, abv


def _ttime(time: list[float], nsam: int) -> float:
    """ms.c:823-833. The root's time is counted twice — once by the
    initializer, once again inside the summation range — a literal quirk
    of the reference source, replicated exactly rather than "corrected"."""
    root = 2 * nsam - 2
    total = time[root]
    for i in range(nsam, 2 * nsam - 1):  # nsam .. root inclusive
        total += time[i]
    return total


def _poisso(u: float, draws: RecordedDrawStream) -> int:
    """ms.c:1030-1046. Draws exactly one `ran1()` call (`ru`); the rest is a
    deterministic accumulation, no further randomness."""
    if u > 30.0:
        raise UnsupportedGasdevBranch(u)
    ru = draws.next()
    p = math.exp(-u)
    if ru < p:
        return 0
    cump = p
    i = 1
    while True:
        p = p * u / i
        cump += p
        if ru <= cump:
            return i
        i += 1


def _pickb(
    nsam: int, time: list[float], abv: list[int], tt: float, draws: RecordedDrawStream
) -> int:
    """ms.c:899-914. One draw per call; falls through to the root index if
    floating-point summation never reaches `x` (matches the C fallback
    `return(i)` after the loop exhausts)."""
    x = draws.next() * tt
    y = 0.0
    for i in range(2 * nsam - 2):
        y += time[abv[i]] - time[i]
        if y >= x:
            return i
    return 2 * nsam - 2


def _tdesn(abv: list[int], tip: int, node: int) -> bool:
    """ms.c:936-946: walk the ancestor chain from `tip` until reaching (or
    passing) `node`."""
    k = tip
    while k < node:
        k = abv[k]
    return k == node


def run_replicate(
    nsam: int, theta: float, draws: RecordedDrawStream
) -> ReplicateResult:
    """One `ms` "gene tree" plus its placed mutations: `gensam()`'s
    `segsitesin==0, theta>0` branch (ms.c:260-281), specialized to the
    always-one-segment minimal model (`len==nsites` always, so
    `tseg = len*(theta/nsites)` is exactly `theta`: scaling a finite double
    by a power of two and back is exact under IEEE754, no rounding)."""
    time, abv = _build_coalescent_tree(nsam, draws)
    tt = _ttime(time, nsam)
    segsit = _poisso(theta * tt, draws)

    rows = [[] for _ in range(nsam)]
    for _ in range(segsit):
        node = _pickb(nsam, time, abv, tt, draws)
        for tip in range(nsam):
            rows[tip].append("1" if _tdesn(abv, tip, node) else "0")

    # ms.c:278 locate()->ordran()->ranvec(): segsit more draws for mutation
    # positions (ms.c's own 4-decimal print truncation excludes them from
    # H1's bit-comparison per R3, but the draws themselves must still be
    # consumed in order for R4 draw parity).
    for _ in range(segsit):
        draws.next()

    # ms.c:192-193 prints genotype rows only when segsites > 0 — a
    # segsites==0 replicate has zero rows, not nsam empty-but-present ones
    # (R3's explicit warning; caught by round-1's independent reimpl.).
    genotype_rows = ["".join(row) for row in rows] if segsit > 0 else []
    return ReplicateResult(segsites=segsit, genotype_rows=genotype_rows)
