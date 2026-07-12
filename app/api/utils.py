"""Check discovery utilities.

Checks are discovered dynamically: every concrete subclass of
:class:`app.checks.base.Check` found under the ``app.checks`` package is
registered by its ``name``. This keeps adding a new check to a single,
self-contained module with no central registry to edit.
"""
import importlib
import inspect
import logging
import pkgutil

import app.checks as checks_package
from app.checks.base import Check

logger = logging.getLogger(__name__)


def discover_checks() -> dict[str, type[Check]]:
    """Return a mapping of ``check name -> check class`` for all concrete checks."""
    registry: dict[str, type[Check]] = {}

    for module_info in pkgutil.walk_packages(checks_package.__path__, prefix=f"{checks_package.__name__}."):
        try:
            module = importlib.import_module(module_info.name)
        except Exception:  # pragma: no cover - defensive: a broken module must not kill discovery
            logger.exception("Failed to import check module %s", module_info.name)
            continue

        for _, obj in inspect.getmembers(module, inspect.isclass):
            if not issubclass(obj, Check) or obj is Check or inspect.isabstract(obj):
                continue
            name = getattr(obj, "name", None)
            if not name:
                logger.warning("Check class %s has no name and will be skipped", obj.__qualname__)
                continue
            registry[name] = obj

    logger.info("Discovered checks: %s", sorted(registry))
    return registry
