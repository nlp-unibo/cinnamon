"""
Ranked "did you mean ...?" suggestions for registration keys.

A ``RegistrationKey`` is a compound of name, namespace and tags, so a typo in
any one of the three produces the same failure: the key is simply not found.
This module scores registered keys against the one that was asked for and
explains *which part* differs, which is usually the whole answer.
"""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import TYPE_CHECKING, Iterable, List

if TYPE_CHECKING:  # pragma: no cover - typing only
    from cinnamon.registry import RegistrationKey

__all__ = [
    "KeySuggestion",
    "closest_string",
    "describe_difference",
    "similarity",
    "suggest_keys",
]

#: Below this, a candidate is noise rather than a suggestion.
MINIMUM_SCORE = 0.55

#: Two distinct strings this similar are probably meant to be the same one.
#: Kept below the obvious 0.8 because short tags transpose badly: 'imbd' and
#: 'imdb' -- a textbook typo -- score only 0.75.
NEAR_DUPLICATE_THRESHOLD = 0.7

#: A candidate whose name is less alike than this is not a near-miss, however
#: well its namespace and tags line up. Without the veto, agreement on the other
#: two components (worth half the score between them) drags unrelated names over
#: the bar -- every key in a namespace becomes a suggestion for every other.
MINIMUM_NAME_SIMILARITY = 0.6

_NAME_WEIGHT = 0.5
_NAMESPACE_WEIGHT = 0.2
_TAG_WEIGHT = 0.3


@dataclass(frozen=True)
class KeySuggestion:
    """A candidate key, how close it is, and why it differs."""

    key: "RegistrationKey"
    score: float
    reason: str

    def __str__(self) -> str:
        return f"{self.key} ({self.reason})"


def similarity(left: str, right: str) -> float:
    """
    Ratio in ``[0, 1]`` of how alike two strings are, ignoring case mismatches.

    Case is compared separately and the better of the two ratios wins, because
    ``SequenceMatcher`` treats 'IMDB' and 'imdb' as sharing *no* characters at
    all -- scoring 0.0 for what is one of the most common tag mistakes there is.
    """
    exact = SequenceMatcher(None, left, right).ratio()
    if left.casefold() == right.casefold():
        return 1.0
    folded = SequenceMatcher(None, left.casefold(), right.casefold()).ratio()
    return max(exact, folded)


def _tag_text(tags: frozenset) -> str:
    return ", ".join(sorted(tags))


def _tag_similarity(left: frozenset, right: frozenset) -> float:
    """Blend set overlap with textual closeness.

    Overlap alone cannot rank a misspelt tag: {'imbd'} shares nothing with
    {'imdb'} *or* with {'sst2'}, so both score zero and the ordering becomes
    arbitrary. Comparing the tag sets as text breaks that tie in favour of the
    one that merely looks misspelt.
    """
    if not left and not right:
        return 1.0
    union = left | right
    overlap = len(left & right) / len(union) if union else 1.0
    return 0.5 * overlap + 0.5 * similarity(_tag_text(left), _tag_text(right))


def _score(target: "RegistrationKey", candidate: "RegistrationKey") -> float:
    return (
        _NAME_WEIGHT * similarity(target.name, candidate.name)
        + _NAMESPACE_WEIGHT * similarity(target.namespace, candidate.namespace)
        + _TAG_WEIGHT * _tag_similarity(target.tags, candidate.tags)
    )


def closest_string(value: str, options: Iterable[str]) -> str | None:
    """The most similar option, or ``None`` when nothing is close enough."""
    ranked = sorted(options, key=lambda option: similarity(value, option), reverse=True)
    if ranked and similarity(value, ranked[0]) >= NEAR_DUPLICATE_THRESHOLD:
        return ranked[0]
    return None


def describe_difference(target: "RegistrationKey", candidate: "RegistrationKey") -> str:
    """
    Say, in words, how *candidate* differs from the key that was asked for.

    Naming the differing component is what turns a list of near-misses into an
    actionable message: "tags differ" points straight at the mistake, where the
    key's string form leaves the reader to diff two lines of text by eye.
    """
    differences: List[str] = []

    if target.name != candidate.name:
        differences.append(f"name '{target.name}' -> '{candidate.name}'")

    if target.namespace != candidate.namespace:
        differences.append(f"namespace '{target.namespace}' -> '{candidate.namespace}'")

    missing = candidate.tags - target.tags
    extra = target.tags - candidate.tags

    # A tag that closely resembles one on the candidate is a typo, not an
    # omission -- report the pairing rather than a bare add/remove.
    typos = []
    for tag in sorted(extra):
        match = closest_string(tag, missing)
        if match is not None:
            typos.append((tag, match))
    paired_extra = {tag for tag, _ in typos}
    paired_missing = {match for _, match in typos}

    for tag, match in typos:
        differences.append(f"tag '{tag}' -> '{match}'")

    remaining_missing = sorted(missing - paired_missing)
    remaining_extra = sorted(extra - paired_extra)
    if remaining_missing:
        differences.append(f"add tags {remaining_missing}")
    if remaining_extra:
        differences.append(f"drop tags {remaining_extra}")

    if not differences:
        return "identical"
    return "; ".join(differences)


def suggest_keys(
    target: "RegistrationKey",
    candidates: Iterable["RegistrationKey"],
    limit: int = 3,
) -> List[KeySuggestion]:
    """
    Rank *candidates* by how likely each is to be what *target* meant.

    A candidate whose name and namespace match exactly is always offered, no
    matter how far its tags are: it is the single most common mistake, and the
    tag score alone can be zero when a tag is misspelt rather than omitted.
    """
    suggestions: List[KeySuggestion] = []

    for candidate in candidates:
        if candidate == target:
            continue

        if candidate.name == target.name and candidate.namespace == target.namespace:
            # Same identity, different tags: always worth offering, and ranked
            # among its peers by how close the tags are.
            score = 0.7 + 0.3 * _tag_similarity(target.tags, candidate.tags)
        else:
            if similarity(target.name, candidate.name) < MINIMUM_NAME_SIMILARITY:
                continue
            score = _score(target, candidate)
            if score < MINIMUM_SCORE:
                continue

        suggestions.append(
            KeySuggestion(
                key=candidate,
                score=score,
                reason=describe_difference(target, candidate),
            )
        )

    suggestions.sort(key=lambda suggestion: (-suggestion.score, str(suggestion.key)))
    return suggestions[:limit]
