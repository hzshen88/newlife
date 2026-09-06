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
