"""List the admissible third-party building blocks installed in this environment.

After installing the wheel a user **has no way to know what is available** — there was no
discovery mechanism at all, and the blocks are scattered across `process_bigraph` and each
optional third-party package. The first real user run reached for a hand-written
`pkgutil.walk_packages`; this is that code, made part of the library.

**Reports, does not judge**: whether a block can actually be admitted also depends on the
shape its `update` returns, and `admit()` hard-fails on that at runtime. This does not
pretend to have checked it.
"""

from __future__ import annotations

import importlib
import inspect
import pkgutil
from typing import Iterator

CANDIDATES = ("process_bigraph", "spatio_flux", "bsp")
"""Which packages to scan.

`bsp` (biosimulator-processes) **has been unimportable for a long time** — recorded
earlier, and still failing today with the same `ProcessTypes` error. It is reported as
broken rather than silently treated as absent.
"""


def _classes(module) -> list[str]:
    from process_bigraph import Process, Step

    return sorted(
        name for name, obj in vars(module).items()
        if inspect.isclass(obj) and issubclass(obj, (Process, Step))
        and obj.__module__ == module.__name__ and not name.startswith("_")
    )


def blocks(packages: tuple[str, ...] = CANDIDATES) -> Iterator[tuple[str, str, list[str]]]:
    """Yield `(top-level package, module name, class names)`.

    **An unimportable package is reported as such** — installed-but-broken and
    not-installed are two different facts.
    """
    for top in packages:
        try:
            root = importlib.import_module(top)
        except Exception as exc:                     # installed-but-broken != absent
            yield top, f"<import failed: {type(exc).__name__}: {str(exc)[:70]}>", []
            continue
        for info in pkgutil.walk_packages(root.__path__, f"{top}."):
            try:
                module = importlib.import_module(info.name)
            except Exception:
                continue                             # broken submodules are normal (optional deps)
            found = _classes(module)
            if found:
                yield top, info.name, found
