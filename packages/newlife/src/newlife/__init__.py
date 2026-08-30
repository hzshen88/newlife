"""newlife — a verifiable profile layer for composable biological simulation.

Owns the scientific semantics the bare runtime does not provide (proposal
v0.6, §3): StateClaim / MechanismSpec / Effect / Resolver contracts, path
authority, read-only alias protection, single-path lowering (the only write
path into any runtime), and canonical evidence traces.

Vendor types (Process, Composite, ...) never leak past the adapter layer;
`process-bigraph` is an optional extra and may only be imported inside
`newlife.adapters.process_bigraph`.
"""
