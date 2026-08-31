# Vendored: Hudson's `ms` (coalescent simulator)

Source: `home.uchicago.edu/~rhudson1/source/mksamples/msdir/{ms.c,streec.c,rand1.c,ms.h}`, fetched 2026-08-31. `ms.h` was missed on the first fetch (only discovered when the plan stage actually compiled `ms.c`/`streec.c`, which both `#include "ms.h"`) and fetched separately during plan drafting — recorded here rather than silently backfilled, per this project's standing rule about catching gaps by running things, not by re-reading a file list more carefully.

Vendored verbatim, unmodified, as the reference oracle for the second-world
question `docs/science-superpowers/questions/2026-08-31-newlife-second-world-ms-coalescent-declarability.md`
(exloop). `ms` carries no formal version tag and is distributed from an
individual academic homepage — the author (Richard Hudson) is retired, and
pages of this kind disappear without notice. Vendoring is the only way to
pin a specific build for cross-language comparison; do not re-fetch and
overwrite these files without updating every SHA-256 this question/plan/
preregistration pipeline pins against them.

No license file accompanies the upstream distribution; usage here is
strictly as a read-only reference oracle for offline, non-redistributed
comparison, consistent with how the field's own tooling (msprime's
`verification.py`) already treats `ms` as a benchmark.

`verification/` holds the small, from-scratch C programs written to
independently verify (not merely assert) this question doc's two
load-bearing bit-exactness claims: `drand48()`'s 48-bit LCG reproduces
bit-for-bit in pure Python (`test_drand48.c`), `log`/`exp` are
IEEE754-identical between a local C build and Python's `math` module
(`test_log.c`, `test_exp_pow.c`), and `-ffp-contract=fast` vs.
`-ffp-contract=off` changes `poisso()`'s internal accumulator bit pattern
in roughly 1/4 of scanned `(u, ru)` combinations but never flips the
integer return value the field actually uses (`poisso_scan.c`).

SHA-256 (`shasum -a 256`):

```
9bb5da6755b56a719966176504485499e5feb3442a0875c09020e25cdfe25622  ms.c
7574be71072ccdcbada67862987a4b89beb0c7ea8fdd977d07da9f34434c9cb4  streec.c
70bd8a05a74e97340341cd45cef7b36b046b74f8c2d47564df6c18d7daf6bbfa  rand1.c
7e22f96d48788b598d8d798753ea104955ecc7baa051fd05eb84601e5e603c98  ms.h
```

**Build note**: `ms.c`/`streec.c` are 1990s-vintage K&R-style C (implicit
`int`, implicit function declarations, `int`-typed functions that fall off
the end without a `return`) that a modern clang (Xcode 16, this
verification's toolchain) rejects by default under C17/C23 defaults. A
reference build for cross-language comparison must compile with:

```
cc -O2 -ffp-contract=off -std=gnu89 \
   -Wno-error=implicit-function-declaration \
   -Wno-error=implicit-int -Wno-error=return-type \
   ms.c streec.c rand1.c -o ms -lm
```

`-ffp-contract=off` is load-bearing (see the FMA finding above and the
question doc); the three `-Wno-error=` flags only suppress *warnings*
about pre-C99 style, not floating-point or optimization behavior — they do
not change what the program computes.

## Verifying the frozen checksums — the script lives in exloop, not here

`vendor/ms/` exists in **both** repos, but the checksum-verification script exists only
on the governance side, next to the frozen preregistration it reads:

```sh
cd ~/Projects/exloop && sh vendor/ms/verify_frozen_checksums.sh
```

It parses the four SHA-256 values out of the frozen World 2 preregistration and compares
them against exloop's copy of these sources (last run: 4/4 PASS). It cannot live here,
because it resolves the preregistration relative to its own repo root.

Do not conclude from this directory alone that no such script exists — that mistake has
already been made once, and it caused a true statement to be removed from the scenario-matrix
artifact as "unverified". Always repo-qualify `vendor/ms/...` paths when citing them.
