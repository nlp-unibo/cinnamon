"""
Static analyzer for cinnamon bound components.

Verifies that configurations are registered correctly with the components
they are bound to. This framework does *not* require a ``Component`` class:
components are plain Python classes referenced by a fully-qualified string path
(see ``Registry.instantiate``). The analyzer therefore checks:

  * that the component path imports to a class;
  * that the configuration's fields are compatible with the component's ``__init__``;
  * that a configuration bound to no component is reported as a warning,
    not an error.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Tuple, Union

from cinnamon.configuration import Configuration
from cinnamon.registry import Registry
from cinnamon.utility.registration import import_class_from_string, locate_module

Key = Tuple[str, str, frozenset]
Analysis = Dict[Key, Tuple[bool, List[str], List[str]]]


@dataclass(frozen=True)
class _ComponentSignature:
    """Hashable summary of a component's ``__init__`` signature."""

    params: frozenset
    required: frozenset
    accepts_var_args: bool
    accepts_var_kwargs: bool


@lru_cache(maxsize=256)
def _get_component_signature(component_path: str) -> _ComponentSignature:
    """
    Import *component_path* and inspect its ``__init__``.

    The result is cached, so repeated lookups for the same component are O(1).
    """
    try:
        component_cls = import_class_from_string(component_path)
    except (ModuleNotFoundError, AttributeError) as exc:
        raise RuntimeError(
            f"Component '{component_path}' cannot be imported: {exc}"
        ) from exc

    try:
        # component_cls is a class object; mypy reads the attribute access as
        # an instance lookup and warns about subclass variance.
        init_sig = inspect.signature(component_cls.__init__)  # type: ignore[misc]
    except (TypeError, ValueError) as exc:
        raise RuntimeError(
            f"Cannot inspect __init__ of '{component_path}': {exc}"
        ) from exc

    params: set[str] = set()
    required: set[str] = set()
    accepts_var_args = accepts_var_kwargs = False

    for name, param in init_sig.parameters.items():
        if name == "self":
            continue
        if param.kind == inspect.Parameter.VAR_KEYWORD:
            accepts_var_kwargs = True
            continue
        if param.kind == inspect.Parameter.VAR_POSITIONAL:
            accepts_var_args = True
            continue
        params.add(name)
        if param.default is inspect.Parameter.empty:
            required.add(name)

    return _ComponentSignature(
        params=frozenset(params),
        required=frozenset(required),
        accepts_var_args=accepts_var_args,
        accepts_var_kwargs=accepts_var_kwargs,
    )


def _check_component_path(component_path: str) -> Tuple[List[str], List[str]]:
    """
    Verify a component path as far as is possible without importing it.

    Returns ``(errors, warnings)``. Walks the path segment by segment through
    :func:`locate_module`, which touches the filesystem only.

    The walk stops at the first segment that is not a module -- normally the
    class name. What that means depends on how much is left over:

    * nothing resolved at all -> the top-level package is missing, which is
      unambiguous and an error;
    * everything but the last segment resolved -> as verified as it gets;
    * something in between -> either a wrong module path or a nested class, and
      no amount of filesystem inspection can tell those apart, so it is a
      warning rather than an error.

    Whether the *class* exists inside the module is not checkable either:
    re-export is the norm, and ``sklearn/svm/__init__.py`` -- to pick the case
    that killed the idea -- defines no classes of its own at all.
    """
    segments = component_path.split(".")
    if len(segments) < 2:
        return (
            [
                f"Component '{component_path}' is not a dotted path; "
                f"expected something like 'package.module.ClassName'."
            ],
            [],
        )

    resolved = 0
    for split in range(1, len(segments)):
        # Presence is reported by `missing`, not by `origin`: a namespace
        # package (a directory with no __init__.py) resolves perfectly well and
        # still has no file of its own to point at.
        _, missing = locate_module(".".join(segments[:split]))
        if missing is not None:
            break
        resolved = split

    if resolved == 0:
        return (
            [
                f"Component '{component_path}' cannot be found: no module or "
                f"package named '{segments[0]}' is importable."
            ],
            [],
        )

    if resolved < len(segments) - 1:
        unresolved = segments[resolved]
        return (
            [],
            [
                f"Component '{component_path}': '{'.'.join(segments[:resolved])}' "
                f"resolves, but '{unresolved}' is not a module. That is expected "
                f"for a nested class, and a typo otherwise -- run with deep "
                f"analysis to be sure."
            ],
        )

    return [], []


def _check_signature(component_path: str, config: Configuration) -> List[str]:
    """Return a list of problems, empty if the signature is compatible."""
    try:
        sig = _get_component_signature(component_path)
    except RuntimeError as exc:
        return [str(exc)]

    config_fields = set(config.fields)
    problems: List[str] = []

    missing_required = sig.required - config_fields
    if missing_required:
        problems.append(
            f"Component '{component_path}' requires parameters "
            f"{sorted(missing_required)} which are missing from configuration "
            f"'{config.__class__.__name__}'."
        )

    if not (sig.accepts_var_args or sig.accepts_var_kwargs):
        extra = config_fields - sig.params
        if extra:
            problems.append(
                f"Configuration '{config.__class__.__name__}' defines fields "
                f"{sorted(extra)} that component '{component_path}' does not "
                f"accept in __init__."
            )

    return problems


def reset_signature_cache() -> None:
    """
    Drop the memoized component signatures.

    ``_get_component_signature`` caches by import path for the lifetime of the
    process. Call this after reloading or redefining component classes so the
    analyzer re-inspects them.
    """
    _get_component_signature.cache_clear()


def analyze_registry(
    registry: type[Registry] = Registry,
    *,
    raise_on_error: bool = False,
    deep: bool = True,
) -> Analysis:
    """
    Analyze every registered configuration's component binding.

    Returns a mapping ``(name, namespace, tags) -> (ok, errors, warnings)``.
    * ``ok`` is ``True`` when there are no errors.
    * An unbound config (``component is None``) is a warning, not an error,
      since unbound configs are valid when used purely as dependencies.

    Args:
        deep: when ``True`` (the default) each component is imported so its
            ``__init__`` can be checked against the configuration's fields.
            When ``False`` the component path is only resolved on the
            filesystem -- no imports, so no cost proportional to how heavy the
            components are, at the price of catching only path mistakes.
            Importing every component of a torch-based project to look for
            typos costs seconds; the shallow pass costs a tenth of a
            millisecond per component.
    """
    if not registry.expanded:
        raise RuntimeError(
            "Registry must be expanded before running the static analyzer."
        )

    results: Analysis = {}

    for key, info in registry.registered_items():
        if info.config is None:
            continue
        errors: List[str] = []
        warnings: List[str] = []

        if info.component is None:
            warnings.append("Configuration is not bound to any component.")
        elif deep:
            errors.extend(_check_signature(info.component, info.config))
        else:
            path_errors, path_warnings = _check_component_path(info.component)
            errors.extend(path_errors)
            warnings.extend(path_warnings)

        results[(key.name, key.namespace, key.tags)] = (
            not bool(errors),
            errors,
            warnings,
        )

        if errors and raise_on_error:
            raise RuntimeError(f"Binding error for {key!r}: {errors}")

    return results


def print_analysis_summary(results: Analysis) -> None:
    """Print a human-readable summary of *results*."""
    total = len(results)
    ok = sum(1 for ok_flag, _, _ in results.values() if ok_flag)
    warned = sum(1 for _, _, warns in results.values() if warns)
    problems = total - ok

    print("=== Static Analyzer Summary ===")
    print(f"Total registered configurations: {total}")
    print(f"Valid bindings: {ok}")
    print(f"Binding problems: {problems}")
    if problems == 0 and warned == 0:
        print("All bindings are valid!")
        return

    for (name, ns, tags), (ok_flag, errs, warns) in sorted(results.items()):
        if ok_flag and not warns:
            continue
        tag_str = f"tags={tags}" if tags else "no tags"
        print(f"\n  • {name} (ns={ns}, {tag_str})")
        # Labelled, because the shallow pass reports both and only errors count
        # towards the exit status.
        for msg in errs:
            print(f"      [error]   {msg}")
        for msg in warns:
            print(f"      [warning] {msg}")


def quick_validate(
    directory: Union[str, Path],
    *,
    external_dirs: Union[List[str], List[Path], None] = None,
) -> Analysis:
    """
    Build the registry for *directory* and immediately run the analyzer.

    NOTE: ``Registry.build`` already expands the DAG, so we must NOT call
    ``Registry.dag_resolution()`` again here (it would raise
    ``AlreadyExpandedException``).
    """
    Registry.build(directory=directory, external_directories=external_dirs)
    return analyze_registry(Registry, raise_on_error=False)
