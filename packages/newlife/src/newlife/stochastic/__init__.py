"""Judging a world whose outcome differs every run.

S0 asks for a byte-identical rerun, and a false S0 becomes `INVALID`. For a world driven by
GPU reductions, concurrency, or a remote model, that is not a high bar — it is an
impossible one, and the whole class produces no verdict at all.

The way out is not a weaker S0. It is to **move the boundary**: sampling is where the
world's randomness lives, judgement reads what sampling wrote and must still reproduce
byte for byte.
"""
