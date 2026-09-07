# Writing your own world

`newlife blocks` lists every `Process`/`Step` installed in your environment — 59 of them
in a default install with the `spatio-flux` extra. If one of them is your model, wire it up
directly. If your simulator is not a process-bigraph `Process` (most are not — tellurium,
COPASI, your own code), wrap it in about twenty lines:

```python
from process_bigraph import Process

class TelluriumODE(Process):
    """Run an Antimony model for `interval`, return the species deltas."""
    config_schema = {"model": "string", "species": "list[string]"}

    def initialize(self, config=None):
        import tellurium as te
        self.rr = te.loada(self.config["model"])
        self.names = list(self.config["species"])

    def inputs(self):  return {"species": "map[float]"}
    def outputs(self): return {"species": "map[float]"}

    def update(self, state, interval):
        for name in self.names:
            self.rr[name] = float(state["species"][name])
        self.rr.resetSelectionLists()
        self.rr.simulate(0.0, float(interval), 2)
        return {"species": {n: float(self.rr[n]) - float(state["species"][n])
                            for n in self.names}}
```

Then declare **what it is allowed to write**, and build the composite:

```python
profile = BiologicalProfile()
profile.register_mechanism(MechanismSpec(
    identity="grn", version="tellurium-2.2.13.1", plane="biological",
    biological_role="gene-regulation", ports=("state",),
    claims=(StateClaim(("species",), "own"),),          # ← the authority declaration
    schedule={"stage": "growth"}, rng_streams=(),
    allowed_effects=frozenset({"StateDelta"}), invariants=()), "grn")

composite = build_composite(
    "my_module:TelluriumODE", identity="grn",
    bindings=(PortBinding("species", ("species",), "add"),),
    lowering={("StateDelta", ("species",)): ("species", "sum-map-add")},
    config={"model": MODEL, "species": ["P"]},
    state_roots={"species": {"P": 0.0}},
    in_wiring={"species": ["species"]}, out_wiring={"species": ["species"]},
    contract=True, interval=DT)                          # ← see the warning below
```

> **`"add"` is a claim about this wrapper, not a default.** The binding's third field says
> whether the value the process returns is a *change* or a *level*, and nothing in the
> process's signature reveals which — `outputs()` gives a type, never that. It is `"add"`
> here because this `update` returns
> `float(self.rr[n]) - float(state["species"][n])`, a difference. **Wrapping a simulator
> that returns absolute values and copying this line writes the level in as though it were
> an increment.** Nothing raises: the run produces plausible numbers in the right units,
> and the pilot records them as covered. Read what your `update` returns and say which of
> the two it is before you write the binding.

Writing anywhere you did not claim raises `newlife.core.errors.CommitAuthorityError` —
**from the contract layer, not from your solver**. That distinction matters: "an exception
was raised" is not the same as "the contract stopped it", and a criterion that conflates
them proves nothing.

> **`interval` is not optional in practice.** It is the process's *own* timestep. If the
> duration you pass to `run_composite` is not a positive integer multiple of it,
> process-bigraph accumulates the requests and fires far fewer times than you asked —
> this used to happen **silently**, producing plausible-looking numbers (251 sample points
> carrying 5 distinct values, final 0.9817 against an analytic 0.9933). `run_composite`
> now hard-fails on the mismatch instead.

The generated `verdict.py` already carries what every question needs identically:
provenance (which build of newlife by source digest, not the version string; which
environment by lockfile hash), the self-reproduction check, and the slot where each
criterion proves it can fail. Replace the placeholder model with the composite above and
keep the rest.

> **Why "proves it can fail" is a required slot**: this project shipped a negative
> control that was true by construction and nobody noticed for a whole milestone.
> See `docs/zh/worlds/019-yield-input-or-outcome.md` §6 (Chinese).

---

# Bringing your own code

`newlife blocks` lists what is *installed*. Two other sources of code are just as common
and neither is covered by that listing: **a local library of your own** (a checkout you
`pip install -e`, not something published to an index) and **code written directly inside
the question folder**. Both run fine today. What neither gets today is a place in the
reproducibility chain — and the failure is silent: the artifact is produced, `S1` stays
green, `newlife audit` returns PASS, and none of it means the run can be repeated.

## Why the version string is not enough

`provenance.package_digest` says it in one line: **"A version string can lie about what is
installed. This cannot."** newlife records its own `newlife_source_sha256` for exactly this
reason, because a source checkout's version is whatever `pyproject.toml` last said —
typically `0.1.0`, forever. Edit the code, rerun, and `env.lock` does not move a byte.

This is not a hypothetical about someone else's project. **newlife and proofroot are
themselves installed editable**, pointing at a source tree; every `dist-info/direct_url.json`
with `dir_info.editable` true is a library in this category. The rule below is the one
newlife already applies to itself, written down so it can be applied to yours.

## Three things, not one

A git commit is the natural answer and it is one third of one. Each of these blocks a
different failure:

| | Blocks | Existing part |
|---|---|---|
| **commit** | losing the code — a digest you cannot resolve back to source | the freeze commit already does this for `prereg.md` |
| **content digest + a dirty check** | *"that is not what ran"* — a commit says nothing about uncommitted edits | `provenance.package_digest` |
| **data checksums** | *"the code was right, the inputs moved"* — for whatever `.gitignore` excludes | `prereg.sh freeze <prereg> [raw-data ...]`, verified by audit's `DATA` line |

Take any one away and something real gets through. **Commit alone**: a working tree with
uncommitted edits produces a verdict whose code exists in no commit, and nobody — including
you — can rebuild it. **Digest alone**: you can prove what ran and never get it back.
**Neither**: a checkout that excludes its inputs is a repository that does not run.

Record all three, and put the first three fields **inside the conjunction**, not merely in
`provenance`. The reasoning is the one already established for solver identity: a fact that
only sits in the artifact cannot change the verdict, so changing the code would leave the
judgement untouched.

## Declare which level you are at, and let it be checked

The point is not that every question must reach the highest level. It is that **the level
is declared and the declaration is mechanically checkable** — the same rule as "waiving is
fine, skipping quietly is not".

| Level | What it adds | Mechanical test | Who can rerun it |
|---|---|---|---|
| `local` | dirty check, source digest, data checksums | `git status --porcelain` empty | **you, on this machine** |
| `portable` | the code is retrievable; the data has a fetch script plus checksums | `git branch -r --contains <commit>` non-empty **after a fetch**, or a `git bundle` containing that commit stored beside the question | anyone with a network |
| `archived` | code *and* data in immutable public archives | the recorded DOI or archive URL resolves — not a placeholder string | an anonymous third party, years later |

Two warnings about the middle row, both found by testing rather than reasoning:
the check reads **remote-tracking branches**, so a stale local view answers for the remote
unless you fetch first; and **a reachable remote is not necessarily a public one** — a
private repository passes this test and still cannot be retrieved by a reviewer. No
mechanical test settles that; say which it is.

## Record the fact, not the promise

A level decays. `portable` today is `local` after the host account is deleted, and this is
the same rot that `verdict_rot` measures for verdicts. So do not write a standing claim:

    reproducibility: portable          # a lie three years from now

Write what was verified, and when:

    code_remote_checked_at_freeze: "github.com/…", commit reachable, 2026-09-07

That sentence stays true forever, because it is about the freeze, not about today. It is
the same reason `unevaluable` exists as a separate verdict state: a conclusion that can no
longer be re-evaluated was not thereby wrong.

## Code and data get separate levels

Publishing code is a push. Publishing data often is not — too large, or licensed so that
it cannot be redistributed at all. A registration is allowed to say

    code: archived
    data: restricted — GAEZ v4 requires registration; fetch script and checksums provided

and that is **better than a single optimistic word covering both**. Claiming the data is
public when a reviewer will hit a login wall is the failure this whole section exists to
prevent.

## A known false negative: submodules

That question was registered and answered
(`questions/2026-09-07-repro-class-gate-false-negatives`, verdict **H0**). One of the four
edge cases tested gets through all three criteria and still does not run:

**A dependency in a git submodule.** The worktree is clean, the commit is reachable on the
remote, the digest and the data checksums both match — and a rebuilt clone has an empty
submodule directory. Each criterion misses it for its own reason: `git status --porcelain`
is empty for an uninitialised submodule; `git ls-files` records a **gitlink, not a file**,
so the submodule's content never enters the digest; and the commit really is on the remote.

The deeper problem is that **a registration has nowhere to say "this repository has a
submodule, clone it with `--recursive`"**, and a rebuild is not allowed to depend on
knowledge that lives outside the registration. Until that is fixed, a repository with
submodules **cannot honestly claim `portable`** on the strength of these three checks
alone; say so, or vendor the dependency.

Three other edge cases — a shallow clone, a `.gitattributes` smudge filter, and an
unfetched LFS pointer — came back `not_a_mutation`, and **that phrase means two different
things**. The shallow clone is genuinely harmless for this rebuild path: the code is
complete and checking out the recorded commit succeeds. The filter and LFS cases more
likely failed to construct over a local `file://` remote at all. **"Tested and fine" must
not stand in for "could not be built"**, and neither says the criteria are safe: finding
one false negative does not mean there is only one.

> **Status**: the levels above are a convention, not yet a gate. Nothing currently refuses
> a freeze that claims `portable` from a repository with no remote — or from one with an
> uninitialised submodule, which is the sharper case now that it is known. Results are
> bound to git 2.50.1; edge behaviour moves with the version.
