"""Role registries — the "abstract class + concrete implementations, chosen at
startup" machinery (architecture.md §7).

Each role has a registry mapping a config string ("webcam", "claude", "lirc",
...) to a concrete class. Adding a new implementation = write a class +
@register it; no other role changes.
"""

ROLES = ("sensor", "classifier", "brain", "actuator", "controller")

_registries: dict[str, dict[str, type]] = {role: {} for role in ROLES}


def register(role: str, name: str):
    """Class decorator: @register("actuator", "lirc")."""
    if role not in _registries:
        raise ValueError(f"unknown role {role!r}; expected one of {ROLES}")

    def decorator(cls: type) -> type:
        _registries[role][name] = cls
        return cls

    return decorator


def create(role: str, name: str, **kwargs):
    """Instantiate the implementation registered for (role, name)."""
    if role not in _registries:
        raise ValueError(f"unknown role {role!r}; expected one of {ROLES}")
    try:
        cls = _registries[role][name]
    except KeyError:
        options = sorted(_registries[role]) or ["<none registered>"]
        raise ValueError(
            f"no {role} implementation named {name!r}; registered: {', '.join(options)}"
        ) from None
    return cls(**kwargs)


def registered(role: str) -> list[str]:
    return sorted(_registries[role])
