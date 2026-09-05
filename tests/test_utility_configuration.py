"""
Tests for cinnamon/utility/configuration.py — the `batched` helper.

On Python < 3.12 the local fallback implementation is active (itertools.batched
does not exist yet); this exercises that fallback. The `>= (3, 12)` branch that
imports from itertools can only be covered by running the suite on Python 3.12+.
"""

from cinnamon.utility.configuration import batched


def test_batched_even_chunks():
    assert list(batched(range(6), 3)) == [(0, 1, 2), (3, 4, 5)]


def test_batched_shorter_last_chunk():
    assert list(batched(range(5), 2)) == [(0, 1), (2, 3), (4,)]


def test_batched_chunk_larger_than_input():
    assert list(batched(range(3), 10)) == [(0, 1, 2)]


def test_batched_empty_input():
    assert list(batched([], 3)) == []
