"""
The scaling claims the documentation makes.

``performance.rst`` and the README say resolution is linear in registrations,
edges and variant keys. A claim in prose rots; a benchmark in CI is flaky. So
what is asserted here is not a duration but the **operation count**, which is
deterministic and is the reason the duration is linear in the first place:

    expand_configuration calls == registrations + dependency edges

exactly, in every shape tried -- one call per node from the topological walk,
plus one memoized hit per edge. If memoization breaks, this number grows with
the shape of the graph rather than its size, and the test says so without
needing a clock or a quiet machine.

That is not hypothetical. The memoized branch of ``expand_configuration``
returned every out-edge instead of only the variant ones, so a caller received
another configuration's key as an alternative to its own. It was found by
reasoning about the two paths, not by a test, and this is the test that would
have caught it going wrong again.

``benchmarks/dag_scaling.py`` has the timings. It is deliberately not run here.
"""

import itertools
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

import pytest

from cinnamon.configuration import Configuration, Param
from cinnamon.registry import RegistrationKey, Registry

ROOT = Path(__file__).resolve().parent.parent
NAMESPACE = "scaling"


def flat(n: int) -> Tuple[Callable[[], None], int, int]:
    def build() -> None:
        for i in range(n):
            cls = type(
                f"Flat{i}",
                (Configuration,),
                {"__annotations__": {"a": int}, "a": Param(1)},
            )
            Registry.register_configuration(
                config=cls(), name=f"flat{i}", namespace=NAMESPACE
            )

    return build, n, 0


def chain(n: int, parents_first: bool = False) -> Tuple[Callable[[], None], int, int]:
    """*n* registrations in one dependency chain.

    *parents_first* reverses the **registration** order, which turns out to
    matter a great deal -- see
    :func:`test_a_deep_chain_resolves_whatever_order_it_was_registered_in`.
    """

    def build() -> None:
        order = range(n - 1, -1, -1) if parents_first else range(n)
        for i in order:
            body: Dict[str, Any] = {"__annotations__": {"a": int}, "a": Param(1)}
            if i:
                body["__annotations__"]["child"] = RegistrationKey
                body["child"] = Param(
                    RegistrationKey(name=f"chain{i - 1}", namespace=NAMESPACE)
                )
            cls = type(f"Chain{i}", (Configuration,), body)
            Registry.register_configuration(
                config=cls(), name=f"chain{i}", namespace=NAMESPACE
            )

    return build, n, n - 1


def fanout(parents: int, children: int) -> Tuple[Callable[[], None], int, int]:
    def build() -> None:
        for j in range(children):
            cls = type(
                f"Child{j}",
                (Configuration,),
                {"__annotations__": {"a": int}, "a": Param(1)},
            )
            Registry.register_configuration(
                config=cls(), name=f"child{j}", namespace=NAMESPACE
            )
        for i in range(parents):
            body: Dict[str, Any] = {
                "__annotations__": {f"d{j}": RegistrationKey for j in range(children)}
            }
            for j in range(children):
                body[f"d{j}"] = Param(
                    RegistrationKey(name=f"child{j}", namespace=NAMESPACE)
                )
            cls = type(f"Parent{i}", (Configuration,), body)
            Registry.register_configuration(
                config=cls(), name=f"parent{i}", namespace=NAMESPACE
            )

    return build, parents + children, parents * children


def _count_expansions(build: Callable[[], None]) -> int:
    """How many times ``expand_configuration`` runs during one resolution."""
    build()
    calls = 0
    original = Registry.expand_configuration.__func__  # type: ignore[attr-defined]

    def counting(cls, *args, **kwargs):
        nonlocal calls
        calls += 1
        return original(cls, *args, **kwargs)

    Registry.expand_configuration = classmethod(counting)  # type: ignore[assignment]
    try:
        Registry.dag_resolution()
    finally:
        Registry.expand_configuration = classmethod(original)  # type: ignore[assignment]
    return calls


@pytest.mark.parametrize(
    "shape",
    [
        flat(20),
        flat(60),
        chain(20),
        chain(60),
        chain(60, parents_first=True),
        fanout(10, 5),
        fanout(20, 5),
        fanout(10, 10),
    ],
    ids=[
        "flat20",
        "flat60",
        "chain20",
        "chain60",
        "chain60-parents-first",
        "fan10x5",
        "fan20x5",
        "fan10x10",
    ],
)
def test_expansion_touches_each_node_and_edge_once(shape, reset_registry):
    """The invariant behind the linear cost, stated exactly.

    Not a bound -- an equality. Anything that revisits a node, or walks an edge
    twice, moves this number and fails here.
    """
    build, registrations, edges = shape

    assert _count_expansions(build) == registrations + edges


def test_doubling_the_graph_doubles_the_work(reset_registry):
    """The claim a reader of the README actually cares about.

    Deterministic, so this is an exact comparison rather than a tolerance.
    """
    small = _count_expansions(chain(50)[0])
    Registry.initialize()
    large = _count_expansions(chain(100)[0])

    assert small == 99 and large == 199
    assert large < 2.1 * small


@pytest.mark.parametrize("parents_first", [False, True], ids=["children", "parents"])
def test_a_deep_chain_resolves_whatever_order_it_was_registered_in(
    parents_first, reset_registry
):
    """Depth is not bounded by the interpreter's recursion limit.

    It used to be, and the *registration* order decided whether you noticed.

    ``dag_resolution`` expanded from the roots downwards. A configuration is
    attached to the root when it has no parent **at the moment it is
    registered**, so registering children first attaches every node to the root
    and they expand shallowest-first -- each parent then finds its child already
    expanded and returns immediately. Registering parents first attaches only
    the top of the chain, and expansion recurses the whole way down: that died
    somewhere between 400 and 600, which is the 491 measured earlier.

    So the earlier claim that 800-deep chains worked was true of a benchmark
    that happened to register children first. Both orders are tested here for
    that reason: one of them would have passed against the old code.

    Resolving in reverse topological order removes the dependence entirely --
    every parent finds its child expanded regardless of how it was registered,
    so depth stays flat.

    1500 is comfortably past the default limit of 1000 and still resolves in
    well under a second.
    """
    depth = 1500
    assert depth > sys.getrecursionlimit()

    build, registrations, _ = chain(depth, parents_first=parents_first)
    build()
    valid, invalid = Registry.dag_resolution()

    assert len(valid) == registrations
    assert not invalid


def test_the_benchmark_script_runs():
    """``benchmarks/dag_scaling.py`` is an artefact, so something has to run it.

    The documentation tells readers to reproduce the constants with it, which is
    the whole reason the page can quote numbers honestly. A benchmark nobody
    executes rots exactly like a demo nobody executes -- and two shipped demos
    here were broken for months for that reason.

    ``--quick`` keeps this under half a second. Only the exit status is checked:
    asserting a duration in CI is how a suite becomes flaky, and the timings are
    for a human reading the table.
    """
    script = ROOT / "benchmarks" / "dag_scaling.py"
    assert script.exists()

    result = subprocess.run(
        [sys.executable, str(script), "--quick"],
        capture_output=True,
        text=True,
        timeout=300,
    )

    assert result.returncode == 0, result.stderr
    assert "worst error against the model" in result.stdout


# -- resolution order is taken from the graph, not from registration --


def _mixed_graph_specs() -> list:
    """A graph with a chain, variants, a container and a shared child.

    Small enough to permute exhaustively, varied enough that any order
    sensitivity in expansion has somewhere to show up.
    """

    def key(name: str) -> RegistrationKey:
        return RegistrationKey(name=name, namespace=NAMESPACE)

    return [
        ("leaf", {"a": int}, {"a": Param(1, variants=[2])}),
        ("other", {"a": int}, {"a": Param(5)}),
        (
            "mid",
            {"child": RegistrationKey, "b": int},
            {"child": Param(key("leaf")), "b": Param(0, variants=[1])},
        ),
        (
            "bag",
            {"deps": List[RegistrationKey]},
            {"deps": Param([key("leaf"), key("other")])},
        ),
        (
            "top",
            {"child": RegistrationKey, "bag": RegistrationKey},
            {"child": Param(key("mid")), "bag": Param(key("bag"))},
        ),
    ]


def _resolve_in_order(specs) -> Tuple[Tuple[str, ...], Tuple[str, ...], int]:
    Registry.initialize()
    for name, annotations, body in specs:
        cls = type(
            f"Mixed_{name}",
            (Configuration,),
            {"__annotations__": annotations, **body},
        )
        Registry.register_configuration(config=cls(), name=name, namespace=NAMESPACE)

    calls = 0
    original = Registry.expand_configuration.__func__  # type: ignore[attr-defined]

    def counting(cls, *args, **kwargs):
        nonlocal calls
        calls += 1
        return original(cls, *args, **kwargs)

    Registry.expand_configuration = classmethod(counting)  # type: ignore[assignment]
    try:
        valid, invalid = Registry.dag_resolution()
    finally:
        Registry.expand_configuration = classmethod(original)  # type: ignore[assignment]

    return (
        tuple(sorted(str(key) for key in valid)),
        tuple(sorted(str(key) for key in invalid)),
        calls,
    )


def test_resolution_does_not_depend_on_registration_order(reset_registry):
    """Every permutation of the same registrations resolves identically.

    Identically in all three respects: the valid keys, the invalid keys, **and
    the number of expansions**. The third is the one with teeth.

    Expanding from the roots downwards took its order from whichever module
    happened to register first -- something no user controls and nothing
    reports. Measured against that resolver, this graph still produced the same
    twelve keys in all 120 orders; what changed was the work, between 6 and 10
    expansions. Order sensitivity showed up as *depth*, not as wrong answers,
    and the consequence was a ``RecursionError`` on a chain long enough for the
    unlucky orders to matter -- which is why it went unnoticed for so long, and
    why asserting only the key sets here would not catch a regression.

    Reverse topological order takes the order from the graph, so the work is
    fixed at ``registrations + edges`` whatever sequence things arrive in. There
    is no strategy to configure: this is the only path, and this test is what
    keeps it the only behaviour.
    """
    specs = _mixed_graph_specs()
    reference = _resolve_in_order(specs)

    valid, invalid, calls = reference
    assert len(valid) == 12 and not invalid
    # Five registrations, five dependency edges.
    assert calls == 10

    for permutation in itertools.permutations(specs):
        assert _resolve_in_order(list(permutation)) == reference, (
            f"registration order changed the outcome: "
            f"{[name for name, _, _ in permutation]}"
        )
