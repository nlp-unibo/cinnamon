"""
Static analysis of registration keys.

Where ``static_analyzer`` checks that a configuration matches the component it
is bound to, this module checks the keys themselves: references that resolve to
nothing, and tags that look like slips of the keyboard.

Both checks exist because a ``RegistrationKey`` is a compound of three loosely
typed parts. Nothing stops you writing ``tags={'imbd'}``, and the failure --
when it comes -- is a lookup miss that names the key you asked for but not the
one you meant.

Run it through ``cmn-check``, or call :func:`analyze_keys` directly."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from itertools import combinations
from typing import Any, List, Sequence, Tuple

from cinnamon.registry import RegistrationKey, Registry
from cinnamon.utility.suggestions import (
    NEAR_DUPLICATE_THRESHOLD,
    KeySuggestion,
    similarity,
    suggest_keys,
)

__all__ = [
    "Severity",
    "KeyFinding",
    "analyze_keys",
    "explain_variant_tags",
    "format_findings",
    "format_variant_explanations",
]

#: Variant tags that name an index rather than a value: ``losses=variant-1``.
#: Minted when the value has no short stable rendering -- a list, a dict, any
#: object that is not a string, number, bool, None or Enum.
_ANONYMOUS_VARIANT = re.compile(r"^(?P<field>.+)=variant-(?P<index>\d+)$")


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"


@dataclass
class KeyFinding:
    """One problem, with enough context to act on it."""

    severity: Severity
    category: str
    message: str
    key: "RegistrationKey | None" = None
    suggestions: List[KeySuggestion] = field(default_factory=list)
    referenced_by: List["RegistrationKey"] = field(default_factory=list)


def _analyze_unresolved(registry: type[Registry]) -> List[KeyFinding]:
    """Report every dependency key that nothing registered."""
    findings: List[KeyFinding] = []
    registered = list(registry._REGISTRY)
    known_namespaces = {key.namespace for key in registered}

    for missing in sorted(registry.unresolved_keys(), key=str):
        referenced_by = sorted(
            (edge[0] for edge in registry._DEPENDENCY_DAG.in_edges(missing)),
            key=str,
        )
        message = f"No configuration is registered under {missing}."
        if missing.namespace not in known_namespaces:
            message += (
                f" Namespace '{missing.namespace}' holds no registrations at all"
                f" -- is its directory passed to Registry.build?"
            )

        findings.append(
            KeyFinding(
                severity=Severity.ERROR,
                category="unresolved-key",
                message=message,
                key=missing,
                suggestions=suggest_keys(missing, registered),
                referenced_by=referenced_by,
            )
        )

    return findings


def _plain_tags(registry: type[Registry]) -> set[str]:
    """Author-written tags only.

    Variant expansion mints tags of its own -- ``weight=2.0``, ``loss.lr=0.1``
    -- and neighbouring variants of one field are near-identical by
    construction. Including them would bury the real findings in noise.
    """
    tags: set[str] = set()
    for key in registry._REGISTRY:
        tags |= key.tags - key.compound_tags - key.hierarchy_tags
    return tags


def _analyze_near_duplicate_tags(registry: type[Registry]) -> List[KeyFinding]:
    """Flag pairs of tags that differ so little they are probably one tag."""
    findings: List[KeyFinding] = []

    for left, right in combinations(sorted(_plain_tags(registry)), 2):
        score = similarity(left, right)
        if score < NEAR_DUPLICATE_THRESHOLD:
            continue

        holders = {
            tag: sorted((key for key in registry._REGISTRY if tag in key.tags), key=str)
            for tag in (left, right)
        }
        if left.casefold() == right.casefold():
            headline = f"Tags '{left}' and '{right}' differ only in case."
        else:
            headline = f"Tags '{left}' and '{right}' are {score:.0%} alike."

        findings.append(
            KeyFinding(
                severity=Severity.WARNING,
                category="near-duplicate-tag",
                message=(
                    f"{headline} "
                    f"'{left}' is used by {len(holders[left])} key(s), "
                    f"'{right}' by {len(holders[right])}. "
                    f"If they mean the same thing, one of them is a typo."
                ),
            )
        )

    return findings


def analyze_keys(registry: type[Registry] = Registry) -> List[KeyFinding]:
    """
    Check every registration key, returning findings worst-first.

    Call after ``Registry.load`` to catch broken references: ``dag_resolution``
    stops at the first one, so the whole picture is only available beforehand.
    Calling it after a successful ``build`` still reports tag problems.
    """
    findings = _analyze_unresolved(registry) + _analyze_near_duplicate_tags(registry)
    findings.sort(key=lambda finding: (finding.severity is not Severity.ERROR,))
    return findings


#: Renderings longer than this are cut. A variant may hold a hundred-element
#: list, and a single unreadable line helps nobody.
_MAX_RENDER = 60


def _render(value: Any) -> str:
    """A readable rendering of whatever a variant field holds, uncapped."""
    if isinstance(value, RegistrationKey):
        tags = ",".join(sorted(value.tags))
        return f"{value.name}[{tags}]" if tags else value.name
    if isinstance(value, Mapping):
        return "{" + ", ".join(f"{k}: {_render(v)}" for k, v in value.items()) + "}"
    if isinstance(value, (list, tuple, set, frozenset)):
        return "[" + ", ".join(_render(item) for item in value) + "]"
    return repr(value)


def _shorten(text: str) -> str:
    """Cap a rendering at one readable line.

    Applied once to the finished string rather than inside :func:`_render`, so
    that a long *container* is cut too -- capping only the scalar branch left a
    hundred-element list rendering across 390 characters.
    """
    return text if len(text) <= _MAX_RENDER else text[: _MAX_RENDER - 3] + "..."


def explain_variant_tags(
    registry: type[Registry] = Registry,
) -> List[Tuple[str, str, str, str]]:
    """
    Say what each indexed variant tag actually holds.

    A variant of a list, a dict, or any other value without a short stable
    rendering is tagged by position -- ``losses=variant-1``. The index is
    deterministic, so keys stay comparable across runs and machines, but it does
    not tell you which losses. This reads the value back off the registered
    configuration and renders it.

    Reported once per configuration and tag, not once per key. A tag means the
    same thing wherever it appears, and a registry with four varying fields
    carries it on a dozen keys -- repeating the explanation for each would bury
    it.

    Requires a resolved registry: the variant configurations only exist once
    ``dag_resolution`` has run.

    Returns:
        ``(name, namespace, tag, rendering)`` tuples, sorted and deduplicated.
    """
    explanations = set()

    for key, info in registry.registered_items():
        if info.config is None:
            continue
        for tag in key.tags:
            match = _ANONYMOUS_VARIANT.match(tag)
            if match is None:
                continue
            field = match.group("field")
            if field not in info.config.fields:
                continue
            explanations.add(
                (
                    key.name,
                    key.namespace,
                    tag,
                    _shorten(_render(getattr(info.config, field))),
                )
            )

    return sorted(explanations)


def format_variant_explanations(
    explanations: Sequence[Tuple[str, str, str, str]],
) -> str:
    """Render :func:`explain_variant_tags` output, or nothing when there is none."""
    if not explanations:
        return ""

    lines = [
        "=== Indexed Variants ===",
        "These tags name a position rather than a value, because a list or dict has",
        "no short stable rendering. Here is what each one holds.",
    ]

    current: Tuple[str, str] | None = None
    width = max(len(tag) for _, _, tag, _ in explanations)
    for name, namespace, tag, rendering in explanations:
        if (name, namespace) != current:
            current = (name, namespace)
            lines.append("")
            lines.append(f"  {name} (ns={namespace})")
        lines.append(f"      {tag:<{width}}  = {rendering}")

    return "\n".join(lines)


def format_findings(findings: Sequence[KeyFinding]) -> str:
    """Render *findings* as a report, or a single line when there are none."""
    if not findings:
        return "No registration key problems found."

    errors = sum(1 for finding in findings if finding.severity is Severity.ERROR)
    warnings = len(findings) - errors

    lines = [
        "=== Registration Key Analysis ===",
        f"Errors: {errors}   Warnings: {warnings}",
    ]

    for finding in findings:
        lines.append("")
        lines.append(f"[{finding.severity.value}] {finding.category}")
        lines.append(f"  {finding.message}")

        if finding.referenced_by:
            lines.append("  referenced by:")
            lines.extend(f"    - {key}" for key in finding.referenced_by)

        if finding.suggestions:
            lines.append("  did you mean:")
            lines.extend(
                f"    - {suggestion.key}\n        ({suggestion.reason})"
                for suggestion in finding.suggestions
            )
        elif finding.severity is Severity.ERROR:
            lines.append("  no similar key is registered.")

    return "\n".join(lines)
