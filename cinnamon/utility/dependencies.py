"""
Shape handling for ``Configuration`` dependency fields.

A ``Configuration`` declares a dependency on another registration by typing a
field as a ``RegistrationKey`` (or a ``Configuration`` subclass). Three shapes
are supported:

    child:   RegistrationKey                    -> SCALAR
    losses:  list[RegistrationKey]              -> LIST
    metrics: dict[str, RegistrationKey]         -> DICT

each optionally wrapped in ``Optional[...]``, and each optionally parameterised
(``RegistrationKey[Loss]``) for the benefit of readers and type checkers.

**Nesting is deliberately unsupported.** ``list[list[RegistrationKey]]`` and
``dict[str, list[RegistrationKey]]`` raise ``TypeError`` at detection time
rather than failing somewhere deeper in registration. One level keeps the
dependency DAG a graph over keys, with no need for a path language to address a
key inside a container.

This module is the single place that knows about these shapes. ``registry.py``
walks dependencies through :func:`iter_dependency_keys` and rebuilds them
through :func:`map_dependency_keys`, so registration, expansion and resolution
stay shape-agnostic."""

from __future__ import annotations

import types
import typing
from collections.abc import Iterator, Mapping
from enum import Enum
from typing import Any, Callable

import cinnamon.configuration
import cinnamon.registry

__all__ = [
    "DependencyShape",
    "dependency_members",
    "dependency_shape",
    "iter_dependency_keys",
    "map_dependency_keys",
]

_SEQUENCE_ORIGINS = (list, tuple, set, frozenset)


class DependencyShape(Enum):
    """How the registration keys of a dependency field are laid out."""

    SCALAR = "scalar"
    LIST = "list"
    DICT = "dict"


def _dependency_types() -> tuple[type, ...]:
    # Resolved lazily: registry and configuration import each other, so the
    # concrete classes are not available while this module is first imported.
    return (
        cinnamon.registry.RegistrationKey,
        cinnamon.configuration.Configuration,
    )


def _is_dependency_type(candidate: Any) -> bool:
    """True for RegistrationKey, Configuration, and Configuration subclasses."""
    if not isinstance(candidate, type):
        return False
    try:
        return issubclass(candidate, _dependency_types())
    except TypeError:  # pragma: no cover - defensive, issubclass on odd objects
        return False


def _unparameterise(annotation: Any) -> Any:
    """``RegistrationKey[Loss]`` -> ``RegistrationKey``; other types unchanged."""
    origin = typing.get_origin(annotation)
    if origin is not None and _is_dependency_type(origin):
        return origin
    return annotation


def _nested_error(field_name: str, annotation: Any) -> TypeError:
    return TypeError(
        f"Field '{field_name}' is annotated {annotation!r}. Nested containers of "
        f"registration keys are not supported: use a flat "
        f"list[RegistrationKey] or dict[str, RegistrationKey]."
    )


def _shape_from_annotation(annotation: Any, field_name: str) -> DependencyShape | None:
    annotation = _unparameterise(annotation)

    if _is_dependency_type(annotation):
        return DependencyShape.SCALAR

    origin = typing.get_origin(annotation)
    args = typing.get_args(annotation)

    if origin in (typing.Union, types.UnionType):
        # Optional[X] and genuine unions alike: the first member that looks like
        # a dependency decides. A concrete value, when there is one, overrides
        # this via _shape_from_value.
        for arg in args:
            if arg is type(None):
                continue
            shape = _shape_from_annotation(arg, field_name=field_name)
            if shape is not None:
                return shape
        return None

    if origin in _SEQUENCE_ORIGINS and args:
        element = args[0]
        if _is_dependency_type(_unparameterise(element)):
            return DependencyShape.LIST
        if _shape_from_annotation(element, field_name=field_name) is not None:
            raise _nested_error(field_name, annotation)
        return None

    if origin is dict and len(args) == 2:
        value_type = args[1]
        if _is_dependency_type(_unparameterise(value_type)):
            return DependencyShape.DICT
        if _shape_from_annotation(value_type, field_name=field_name) is not None:
            raise _nested_error(field_name, annotation)
        return None

    return None


def _shape_from_value(value: Any, field_name: str) -> DependencyShape | None:
    if isinstance(value, _dependency_types()):
        return DependencyShape.SCALAR

    if isinstance(value, Mapping):
        items = list(value.values())
    elif isinstance(value, _SEQUENCE_ORIGINS):
        items = list(value)
    else:
        return None

    shape = DependencyShape.DICT if isinstance(value, Mapping) else DependencyShape.LIST

    for item in items:
        if isinstance(item, _dependency_types()):
            return shape
        if _shape_from_value(item, field_name=field_name) is not None:
            raise _nested_error(field_name, type(value))

    # Empty, or holding no keys at all: the annotation decides.
    return None


def dependency_shape(
    field_name: str,
    annotation: Any,
    value: Any,
) -> DependencyShape | None:
    """
    Classify *field_name* as a dependency field, or ``None`` if it is not one.

    The runtime *value* is consulted first, so a union annotation such as
    ``RegistrationKey | list[RegistrationKey]`` resolves to whatever the field
    actually holds. The annotation is the fallback, which is what makes an
    unset optional dependency (``dict[str, RegistrationKey] | None = None``)
    still register as one.

    Raises:
        ``TypeError``: if the field nests containers of registration keys.
    """
    shape = _shape_from_value(value, field_name=field_name)
    if shape is not None:
        return shape
    return _shape_from_annotation(annotation, field_name=field_name)


def iter_dependency_keys(value: Any) -> Iterator["cinnamon.registry.RegistrationKey"]:
    """
    Yield every ``RegistrationKey`` held by *value*, whatever its shape.

    Accepts a bare key, a list/tuple/set of keys, a mapping of them, or
    ``None``. Non-key members are skipped, so a partially resolved container
    (keys already swapped for ``Configuration`` instances) iterates cleanly.
    """
    registration_key = cinnamon.registry.RegistrationKey

    if isinstance(value, registration_key):
        yield value
        return

    if isinstance(value, Mapping):
        members: Any = value.values()
    elif isinstance(value, _SEQUENCE_ORIGINS):
        members = value
    else:
        return

    for member in members:
        if isinstance(member, registration_key):
            yield member


def dependency_members(value: Any) -> Iterator[Any]:
    """
    Yield the raw members of *value*, whatever their type.

    Unlike :func:`iter_dependency_keys` nothing is filtered out, so callers can
    check that a dependency really holds registration keys and report the ones
    that do not. ``None`` yields nothing, which is how an unset optional
    dependency stays legal.
    """
    if value is None:
        return

    if isinstance(value, Mapping):
        yield from value.values()
    elif isinstance(value, _SEQUENCE_ORIGINS):
        yield from value
    else:
        yield value


def map_dependency_keys(value: Any, function: Callable[[Any], Any]) -> Any:
    """
    Rebuild *value* with *function* applied to every ``RegistrationKey`` in it.

    The container shape is preserved, so a ``dict[str, RegistrationKey]`` maps
    to a ``dict[str, Configuration]`` under the same string labels. Members that
    are not keys are passed through untouched.
    """
    registration_key = cinnamon.registry.RegistrationKey

    if isinstance(value, registration_key):
        return function(value)

    if isinstance(value, Mapping):
        return {
            label: function(member) if isinstance(member, registration_key) else member
            for label, member in value.items()
        }

    if isinstance(value, _SEQUENCE_ORIGINS):
        mapped = [
            function(member) if isinstance(member, registration_key) else member
            for member in value
        ]
        return type(value)(mapped) if not isinstance(value, list) else mapped

    return value
