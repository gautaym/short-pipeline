"""Format registry.

Every module under reel_engine.formats is imported on first use, and classes decorated with
@register become available to the CLI. Adding a format means adding a module; nothing in
core or the CLI needs to change.
"""
import importlib
import pkgutil

from .base import EndCard, Format, Option, Twist

_REGISTRY: dict[str, type[Format]] = {}
_discovered = False


def register(cls: type[Format]) -> type[Format]:
    name = cls.__dict__.get("name")
    if not name:
        raise TypeError(f"{cls.__name__} needs a 'name' to be registered")
    if name in _REGISTRY and _REGISTRY[name] is not cls:
        raise ValueError(f"format name '{name}' is already registered by {_REGISTRY[name].__name__}")
    _REGISTRY[name] = cls
    return cls


def discover() -> None:
    global _discovered
    if _discovered:
        return
    for mod in pkgutil.walk_packages(__path__, __name__ + "."):
        importlib.import_module(mod.name)
    _discovered = True


def all_formats() -> list[type[Format]]:
    """Registered formats in rotation order."""
    discover()
    return sorted(_REGISTRY.values(), key=lambda c: (c.order, c.name))


def names() -> list[str]:
    return [c.name for c in all_formats()]


def random_pool() -> list[str]:
    return [c.name for c in all_formats() if c.in_random_pool]


def get(name: str) -> type[Format]:
    discover()
    try:
        return _REGISTRY[name]
    except KeyError:
        raise SystemExit(f"unknown format '{name}'. Available: {', '.join(names())}") from None


__all__ = ["EndCard", "Format", "Option", "Twist", "register", "discover", "all_formats", "names", "random_pool", "get"]
