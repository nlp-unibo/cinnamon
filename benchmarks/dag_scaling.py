"""
Measure how ``Registry.dag_resolution`` scales.

    python benchmarks/dag_scaling.py
    python benchmarks/dag_scaling.py --quick     # small shapes, for a smoke test

The documentation quotes a cost model. Absolute milliseconds are a property of
the machine that produced them, so rather than asking anyone to trust the
numbers on the page, this reproduces them: run it, and compare.

Four shapes, because "how does it scale" has more than one answer depending on
what you add:

``flat``
    Registrations with no dependencies and no variants. Isolates the per
    registration cost.
``chain``
    A single dependency chain, so edges grow with registrations and the graph is
    as deep as it can be.
``fanout``
    Many parents depending on a shared pool of children. Isolates the per edge
    cost, since registrations stay nearly constant while edges multiply.
``variants``
    Registrations that expand. Isolates the cost of a derived configuration,
    which is the expensive one: it is copied, resolved and validated.

What the shapes have in common is more interesting than the constants: every one
of them is linear. Doubling the input doubles the time, in all four directions.
"""

import platform
import sys
import time
from typing import Any, Callable, Dict, List, Tuple

from cinnamon.configuration import Configuration, Param
from cinnamon.registry import RegistrationKey, Registry

NAMESPACE = "benchmark"

#: Fitted on the machine named in the output. Reported so a run can disagree
#: with it: a shape that misses by much more than the others is the interesting
#: result, not the constants.
COST_PER_REGISTRATION_MS = 0.034
COST_PER_EDGE_MS = 0.045
COST_PER_VARIANT_KEY_MS = 0.113

#: What each shape reports, so the model can be evaluated against it.
Shape = Tuple[str, Callable[[], None], Dict[str, int]]


def flat(n: int) -> Shape:
    """*n* registrations, nothing else."""

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

    return f"flat {n}", build, {"registrations": n, "edges": 0, "variant_keys": 0}


def chain(n: int) -> Shape:
    """*n* registrations in one dependency chain, so the graph is *n* deep."""

    def build() -> None:
        for i in range(n):
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

    return (
        f"chain {n}",
        build,
        {"registrations": n, "edges": n - 1, "variant_keys": 0},
    )


def fanout(parents: int, children: int) -> Shape:
    """*parents* configurations each depending on all *children*."""

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

    return (
        f"fanout {parents}x{children}",
        build,
        {
            "registrations": parents + children,
            "edges": parents * children,
            "variant_keys": 0,
        },
    )


def variants(n: int, each: int) -> Shape:
    """*n* registrations, each expanding to *each* configurations."""

    def build() -> None:
        for i in range(n):
            cls = type(
                f"Varied{i}",
                (Configuration,),
                {
                    "__annotations__": {"a": int},
                    "a": Param(0, variants=list(range(1, each))),
                },
            )
            Registry.register_configuration(
                config=cls(), name=f"varied{i}", namespace=NAMESPACE
            )

    return (
        f"variants {n}x{each}",
        build,
        {"registrations": n, "edges": 0, "variant_keys": n * (each - 1)},
    )


def measure(build: Callable[[], None], repeats: int = 3) -> float:
    """Best of *repeats*, in milliseconds.

    Best rather than mean: the thing being measured is deterministic, so a slower
    run only ever means the machine was busy.
    """
    best = float("inf")
    for _ in range(repeats):
        Registry.initialize()
        build()
        start = time.perf_counter()
        Registry.dag_resolution()
        best = min(best, time.perf_counter() - start)
    return best * 1000


def predict(counts: Dict[str, int]) -> float:
    return (
        COST_PER_REGISTRATION_MS * counts["registrations"]
        + COST_PER_EDGE_MS * counts["edges"]
        + COST_PER_VARIANT_KEY_MS * counts["variant_keys"]
    )


#: A handful of small shapes, so that CI can prove this script still runs
#: without spending fourteen seconds on it. The full set is for humans.
QUICK_SHAPES: List[Shape] = [
    flat(50),
    chain(50),
    fanout(10, 5),
    variants(25, 4),
]

SHAPES: List[Shape] = [
    flat(250),
    flat(500),
    flat(1000),
    flat(2000),
    chain(250),
    chain(500),
    fanout(100, 10),
    fanout(200, 10),
    fanout(400, 10),
    fanout(200, 20),
    variants(250, 4),
    variants(500, 4),
    variants(250, 8),
]


def main() -> None:
    quick = "--quick" in sys.argv[1:]
    shapes = QUICK_SHAPES if quick else SHAPES

    print(f"python   {sys.version.split()[0]}")
    print(f"platform {platform.platform()}")
    print(f"machine  {platform.processor() or platform.machine()}")
    print()
    print(
        "model    "
        f"{COST_PER_REGISTRATION_MS} ms x registrations"
        f"  +  {COST_PER_EDGE_MS} ms x edges"
        f"  +  {COST_PER_VARIANT_KEY_MS} ms x variant keys"
    )
    print()

    header = (
        f"{'shape':18s} {'regs':>6s} {'edges':>6s} {'variants':>9s} "
        f"{'ms':>8s} {'model':>8s} {'error':>7s}"
    )
    print(header)
    print("-" * len(header))

    worst = 0.0
    for label, build, counts in shapes:
        milliseconds = measure(build)
        predicted = predict(counts)
        error = (predicted - milliseconds) / milliseconds * 100
        worst = max(worst, abs(error))
        print(
            f"{label:18s} {counts['registrations']:6d} {counts['edges']:6d} "
            f"{counts['variant_keys']:9d} {milliseconds:8.1f} {predicted:8.1f} "
            f"{error:+6.0f}%"
        )

    print()
    print(f"worst error against the model: {worst:.0f}%")
    if quick:
        print("(--quick: small shapes only, so the errors mean little)")


if __name__ == "__main__":
    main()
