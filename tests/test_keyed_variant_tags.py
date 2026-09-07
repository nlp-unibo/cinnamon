"""
How a parent's variant keys are derived from a scalar dependency's alternatives.

A parent's variant tags are the *child key's tags*, prefixed by the field name.
The child's ``name`` and ``namespace`` are discarded, so two alternatives that
share a tag set -- or carry none -- collapse into one parent key.

These tests pin the behaviour as it is, including the collapse. They are a memo,
not an endorsement: see issue #31 for the analysis and the candidate fixes. If a
future change makes the collapsing cases produce one key per alternative, these
tests are *supposed* to fail, and the failure is the signal to update the
warning in ``docsrc/source/dependencies.rst`` alongside them.
"""

from typing import Set

import networkx as nx
import pytest

from cinnamon.configuration import Configuration, Param
from cinnamon.registry import RegistrationKey, Registry

NAMESPACE = "keyed-variants"


class Child(Configuration):
    value: int = Param(0)


def _key(name: str, tags: Set[str] | None = None) -> RegistrationKey:
    return RegistrationKey(name=name, tags=tags or set(), namespace=NAMESPACE)


def _resolve(default: RegistrationKey, alternatives: list[RegistrationKey]):
    """Register a parent varying one scalar dependency, and resolve."""
    declared = alternatives

    class Parent(Configuration):
        dep: RegistrationKey = Param(default, variants=declared)

    for key in [default, *alternatives]:
        Registry.register_configuration(
            config=Child(), name=key.name, tags=key.tags, namespace=key.namespace
        )
    Registry.register_configuration(config=Parent(), name="parent", namespace=NAMESPACE)

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


def test_alternatives_sharing_a_tag_set_collapse_into_one_key(reset_registry):
    """Two alternatives, one parent key. One of them is dropped.

    Which one survives is not deterministic across processes -- the declared
    order is replaced by ``list(set(...))`` during expansion -- so this asserts
    the collapse, not the winner.
    """
    parents = _resolve(
        _key("loader", {"base"}),
        [_key("loader-a", {"fast"}), _key("loader-b", {"fast"})],
    )

    assert len(parents) == 2, "expected the two 'fast' alternatives to collapse"
    varied = [key for key in parents if key.tags]
    assert len(varied) == 1
    assert varied[0].tags == {"dep.fast"}
    assert _dep_of(varied[0]) in {"loader-a", "loader-b"}


def test_untagged_alternatives_collapse_into_the_parents_own_key(reset_registry):
    """Alternatives distinguished only by name produce no parent variant at all.

    The child contributes no tags, so the derived variant key equals the parent's
    own key. Every alternative is lost, and the surviving key still resolves to
    the default.
    """
    parents = _resolve(_key("loader-base"), [_key("loader-csv"), _key("loader-json")])

    assert len(parents) == 1, "expected both untagged alternatives to be lost"
    assert parents[0].tags == set()
    assert _dep_of(parents[0]) == "loader-base"


def test_the_untagged_case_leaves_a_self_loop_in_the_graph(reset_registry):
    """The collapse is also a graph defect, not only a missing key.

    ``add_edge(key, variant_key)`` with ``variant_key == key`` is a self-loop, so
    the dependency graph stops being a DAG. ``check_registration_graph`` runs
    before expansion, which is why nothing reports it.
    """
    _resolve(_key("loader-base"), [_key("loader-csv")])

    dag = Registry._DEPENDENCY_DAG
    assert [str(node) for node, _ in nx.selfloop_edges(dag)] == [
        f"name=parent--namespace={NAMESPACE}"
    ]
    assert not nx.is_directed_acyclic_graph(dag)


@pytest.mark.parametrize("alternative_tags", [{"csv"}, {"json"}])
def test_a_single_tagged_alternative_always_yields_two_keys(
    reset_registry, alternative_tags
):
    """Sanity check on the boundary: one distinct tag is enough to stay separate."""
    parents = _resolve(_key("loader", {"base"}), [_key("loader", alternative_tags)])

    assert len(parents) == 2
