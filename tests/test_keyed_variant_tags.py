"""
How a parent's variant keys are derived from a scalar dependency's alternatives.

A parent's variant tags are the *child key's tags*, prefixed by the field name.
The child's ``name`` and ``namespace`` are discarded, so two alternatives that
share a tag set -- or carry none -- collapse into one parent key.

The collapse used to be silent: the second registration was skipped, the second
``add_edge`` was a no-op, and the project came out with fewer keys than it
declared with nothing to say so. It is a ``VariantKeyCollisionException`` now.
The derivation itself is unchanged -- a key format that carries the child's
name is a 3.0 question -- so these tests pin *where the loss was* as much as
what replaced it.
"""

from typing import Set

import networkx as nx
import pytest

from cinnamon.configuration import Configuration, Param
from cinnamon.registry import RegistrationKey, Registry
from cinnamon.utility.exceptions import (
    NotADAGException,
    VariantKeyCollisionException,
)

NAMESPACE = "keyed-variants"


class Child(Configuration):
    value: int = Param(0)


def _key(name: str, tags: Set[str] | None = None) -> RegistrationKey:
    return RegistrationKey(name=name, tags=tags or set(), namespace=NAMESPACE)


def _register(default: RegistrationKey, alternatives: list[RegistrationKey]):
    """Register a parent varying one scalar dependency."""
    declared = alternatives

    class Parent(Configuration):
        dep: RegistrationKey = Param(default, variants=declared)

    for key in [default, *alternatives]:
        Registry.register_configuration(
            config=Child(), name=key.name, tags=key.tags, namespace=key.namespace
        )
    Registry.register_configuration(config=Parent(), name="parent", namespace=NAMESPACE)


def _resolve(default: RegistrationKey, alternatives: list[RegistrationKey]):
    """Register as above, resolve, and return the parent's keys."""
    _register(default, alternatives)
    valid, _ = Registry.dag_resolution()
    return sorted((key for key in valid if key.name == "parent"), key=str)


def _dep_of(key: RegistrationKey) -> str:
    return Registry.retrieve_configuration_info(registration_key=key).config.dep.name


def test_distinct_tags_give_one_parent_key_per_alternative(reset_registry):
    """The documented, working case: alternatives tagged apart stay apart."""
    parents = _resolve(
        _key("loader", {"csv"}),
        [_key("loader", {"json"}), _key("loader", {"parquet"})],
    )

    assert len(parents) == 3
    assert {frozenset(key.tags) for key in parents} == {
        frozenset(),
        frozenset({"dep.json"}),
        frozenset({"dep.parquet"}),
    }


def test_child_variants_propagate_as_prefixed_tags(reset_registry):
    """The common case: the child varies its own parameter, the parent inherits."""

    class VaryingChild(Configuration):
        sentences: int = Param(1, variants=[2])

    class Parent(Configuration):
        strategy: RegistrationKey = Param(_key("strategy", {"truncate"}))

    Registry.register_configuration(
        config=VaryingChild(), name="strategy", tags={"truncate"}, namespace=NAMESPACE
    )
    Registry.register_configuration(config=Parent(), name="parent", namespace=NAMESPACE)

    valid, _ = Registry.dag_resolution()
    parent_tags = {frozenset(key.tags) for key in valid if key.name == "parent"}

    assert parent_tags == {
        frozenset(),
        frozenset({"strategy.sentences=2", "strategy.truncate"}),
    }


def test_alternatives_sharing_a_tag_set_are_refused(reset_registry):
    """Two alternatives, one derived key. One of them used to be dropped.

    Which one survived was not even deterministic across processes: the
    declared order went through a set on the way to the variant indexes.
    """
    _register(
        _key("loader", {"base"}),
        [_key("loader-a", {"fast"}), _key("loader-b", {"fast"})],
    )

    with pytest.raises(VariantKeyCollisionException) as raised:
        Registry.dag_resolution()

    assert "dep.fast" in str(raised.value)


def test_untagged_alternatives_are_refused(reset_registry):
    """Alternatives distinguished only by name contribute no tags at all.

    The derived key is then the parent's own, so the variant and the
    configuration it varies could not be told apart.
    """
    _register(_key("loader-base"), [_key("loader-csv"), _key("loader-json")])

    with pytest.raises(VariantKeyCollisionException) as raised:
        Registry.dag_resolution()

    assert "derives its own parent's key" in str(raised.value)


def test_the_untagged_case_no_longer_leaves_a_self_loop(reset_registry):
    """The collapse was a graph defect as well as a missing key.

    ``add_edge(key, variant_key)`` with ``variant_key == key`` is a self-loop,
    and ``check_registration_graph`` runs *before* expansion, so nothing saw
    it. The edge is never added now, and ``check_graph_topology`` runs again
    after expansion as a backstop.
    """
    _register(_key("loader-base"), [_key("loader-csv")])

    with pytest.raises(VariantKeyCollisionException):
        Registry.dag_resolution()

    dag = Registry._DEPENDENCY_DAG
    assert list(nx.selfloop_edges(dag)) == []


def test_a_variant_key_registered_by_hand_is_reused(reset_registry):
    """Deriving onto an existing key is deliberate, and is not a collision.

    Registering the derived key yourself is how a single variant's
    configuration gets overridden: expansion finds it in the graph and in the
    registry and leaves both alone rather than registering over them.
    """
    Registry.register_configuration(
        config=Child(value=99), name="parent", tags={"dep.json"}, namespace=NAMESPACE
    )

    parents = _resolve(_key("loader", {"csv"}), [_key("loader", {"json"})])

    assert {frozenset(key.tags) for key in parents} == {
        frozenset(),
        frozenset({"dep.json"}),
    }
    varied = next(key for key in parents if key.tags)
    kept = Registry.retrieve_configuration_info(registration_key=varied).config
    assert kept.value == 99, "the hand-registered configuration was overwritten"


def test_expansion_is_checked_for_topology_of_its_own(reset_registry):
    """The backstop fires even if something else adds a variant self-loop."""
    Registry.register_configuration(
        config=Child(), name="lonely", namespace=NAMESPACE
    )
    key = _key("lonely")

    original = Registry.expand_configuration

    def sneak(**kwargs):
        result = original(**kwargs)
        Registry._DEPENDENCY_DAG.add_edge(key, key, type="variant")
        return result

    Registry.expand_configuration = staticmethod(sneak)
    try:
        with pytest.raises(NotADAGException):
            Registry.dag_resolution()
    finally:
        Registry.expand_configuration = original


@pytest.mark.parametrize("alternative_tags", [{"csv"}, {"json"}])
def test_a_single_tagged_alternative_always_yields_two_keys(
    reset_registry, alternative_tags
):
    """Sanity check on the boundary: one distinct tag is enough to stay separate."""
    parents = _resolve(_key("loader", {"base"}), [_key("loader", alternative_tags)])

    assert len(parents) == 2
