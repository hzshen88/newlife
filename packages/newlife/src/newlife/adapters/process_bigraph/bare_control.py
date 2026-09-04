"""Bare process-bigraph controls that deliberately bypass newlife."""

from __future__ import annotations

from typing import Any

from process_bigraph import Composite, allocate_core
from process_bigraph.processes.growth_division import Grow


def bare_trajectory(*, initial_mass: float, rate: float, steps: int) -> list[float]:
    """Run ``Grow`` on bare process-bigraph and return the mass trajectory."""
    core = _core()
    state: dict[str, Any] = {
        "mass": initial_mass,
        "grow": {
            "_type": "process",
            "address": "local:Grow",
            "config": {"rate": rate},
            "inputs": {"mass": ["mass"]},
            "outputs": {"mass": ["mass"]},
            "interval": 1.0,
        },
    }
    composite = Composite({"state": state}, core=core)
    trajectory = [float(composite.state["mass"])]
    for _ in range(steps):
        composite.run(1.0)
        trajectory.append(float(composite.state["mass"]))
    return trajectory


def _core():
    core = allocate_core()
    core.register_link("Grow", Grow)
    return core


# --- 第十六个里程碑：一个真正独立的第三方包（spatio-flux 1.4.0）---


def monod_trajectory(
    *, initial_mass: float, glucose: float, steps: int
) -> list[tuple[float, dict[str, float]]]:
    """Run ``MonodKinetics`` on bare process-bigraph and return its trajectory."""
    try:
        import spatio_flux
        from spatio_flux.processes.monod_kinetics import MonodKinetics
    except ImportError as exc:
        raise SystemExit(
            "spatio-flux is not installed; this is an environment error, not a verdict. "
            "Install with: uv sync --package newlife --extra process-bigraph "
            f"--extra spatio-flux. Original error: {exc}"
        ) from exc

    core = allocate_core()
    spatio_flux.register_types(core)          # 第三方交付的类型词表
    core.register_link("MonodKinetics", MonodKinetics)

    state: dict[str, Any] = {
        "mass": initial_mass,
        "local": {"glucose": glucose},
        "exchange": {"glucose": 0.0},
        "kin": {
            "_type": "process",
            "address": "local:MonodKinetics",
            "config": {},
            "inputs": {"biomass": ["mass"], "substrates": ["local"]},
            "outputs": {"biomass": ["mass"], "substrates": ["exchange"]},
            "interval": 1.0,
        },
    }
    composite = Composite({"state": state}, core=core)
    out = [(float(composite.state["mass"]), dict(composite.state["exchange"]))]
    for _ in range(steps):
        composite.run(1.0)
        out.append((float(composite.state["mass"]), dict(composite.state["exchange"])))
    return out


# --- 第十七个里程碑：一个求解器背后的第三方 process（spatio-flux 的 dFBA）---

FIELDS = ("glucose", "acetate", "biomass")


def dfba_trajectory(
    *, glucose: float, acetate: float, biomass: float, steps: int
) -> list[dict[str, float]]:
    """Run ``DynamicFBA`` on bare process-bigraph with its bundled E. coli model."""
    try:
        import spatio_flux
        from spatio_flux.processes.dfba import MODEL_REGISTRY_DFBA, DynamicFBA
    except ImportError as exc:
        raise SystemExit(
            "spatio-flux or cobra is not installed; this is an environment error, "
            "not a verdict. Install with: uv sync --package newlife "
            f"--extra process-bigraph --extra spatio-flux. Original error: {exc}"
        ) from exc

    core = allocate_core()
    spatio_flux.register_types(core)
    core.register_link("DynamicFBA", DynamicFBA)

    state: dict[str, Any] = {
        "fields": {"glucose": glucose, "acetate": acetate, "biomass": biomass},
        "fba": {
            "_type": "process",
            "address": "local:DynamicFBA",
            "config": dict(MODEL_REGISTRY_DFBA["ecoli core"]),
            "inputs": {
                "substrates": {"glucose": ["fields", "glucose"],
                               "acetate": ["fields", "acetate"]},
                "biomass": ["fields", "biomass"],
            },
            "outputs": {
                "substrates": {"glucose": ["fields", "glucose"],
                               "acetate": ["fields", "acetate"]},
                "biomass": ["fields", "biomass"],
            },
            "interval": 1.0,
        },
    }
    composite = Composite({"state": state}, core=core)
    out = [normalise_fields(composite.state["fields"])]
    for _ in range(steps):
        composite.run(1.0)
        out.append(normalise_fields(composite.state["fields"]))
    return out


def normalise_fields(fields: Any) -> dict[str, float]:
    """Normalize third-party numeric scalar values to Python ``float``."""
    return {k: float(fields[k]) for k in FIELDS}


def solver_identity() -> dict[str, str]:
    """Return the optimization interface and solver version used by dFBA."""
    from cobra.io import load_model
    import swiglpk

    return {
        "optlang_interface": load_model("textbook").solver.interface.__name__,
        "glpk_version": str(swiglpk.glp_version()),
    }
