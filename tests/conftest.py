"""Shared pytest fixtures.

Fixtures live here rather than in ``fixtures.py`` so pytest injects them by name.
Importing a fixture explicitly shadows it with the test's own parameter, which is
both redundant and a lint error (F811).
"""

import pytest

from cinnamon.registry import Registry


@pytest.fixture
def reset_registry():
    """Return the global ``Registry`` to a clean state before each test."""
    Registry.initialize()
    yield
    Registry.initialize()


@pytest.fixture
def expand_registry():
    """Mark the registry as expanded, restoring the previous flag afterwards."""
    previous = Registry.expanded
    Registry.expanded = True
    yield
    Registry.expanded = previous
