.. _performance:

Performance
*********************************************

The short answer: **resolution is linear in the size of your project, and the
constants are small enough that it is not the thing you will be waiting for.**

A 500-registration project with 1,000 dependency edges resolves in about 60 ms.
Importing scikit-learn on the same machine takes 564 ms. Building the registry is
not what costs you time — which is the point of binding components by import path
rather than importing them, and why ``cmn-check`` can validate a whole project
without loading a single component.

=============================================
The cost model
=============================================

Three things drive the cost, and each contributes independently:

.. code-block:: text

    resolution ≈ 0.034 ms × registrations
                + 0.045 ms × dependency edges
                + 0.113 ms × variant configurations

A *dependency edge* is one ``RegistrationKey`` reachable from one field —
a ``list`` of five keys is five edges. A *variant configuration* is one derived
by expansion, so a field with ``variants=[a, b]`` on a configuration contributes
two.

Variant configurations are the expensive term, by roughly three to one, because
each one is copied, has its dependencies resolved, and has its conditions
validated. If a project is slow to resolve, that is where the time is, and the
number to look at is how many configurations the sweep expands to rather than
how many you wrote.

The constants belong to one machine. **Do not trust them; reproduce them:**

.. code-block:: bash

    python benchmarks/dag_scaling.py

which prints the measured time for thirteen shapes alongside what the model
predicts. On the machine it was fitted on — Python 3.13, Ryzen 9 5900 — the
worst disagreement is 16%.

=============================================
What it looks like in practice
=============================================

============================  ==============  =========  ============
Project                       Registrations   Edges      Resolution
============================  ==============  =========  ============
``examples/`` in this repo    9               11         1.0 ms
A large research project      500             1,000      ~62 ms
Deliberately unreasonable     2,000           4,000      ~250 ms
============================  ==============  =========  ============

The first row is measured; the other two are the model, which the benchmark
confirms to within 16%.

For comparison, on the same machine: ``import pandas`` costs 171 ms and
``import sklearn`` 564 ms. A project big enough for resolution to be noticeable
is one where importing a single component costs more than resolving everything.

=============================================
Why it stays linear
=============================================

Every configuration is expanded exactly once. Resolution walks the dependency
graph in reverse topological order, so a configuration's children are always
expanded before it is, and the second visit — the one that arrives along a
dependency edge — returns a memoized answer instead of recursing.

That gives an exact invariant rather than an estimate:

.. code-block:: text

    expand_configuration calls == registrations + dependency edges

which ``tests/test_scaling.py`` asserts as an equality on every graph shape. It
is a deterministic count rather than a duration, so it holds on a busy CI runner
and fails the moment anything starts revisiting nodes. A quadratic regression
cannot pass it.

=============================================
Depth
=============================================

Dependency chains are not limited by Python's recursion limit. A chain of 1,500
configurations resolves, with the interpreter default of 1,000, because
expansion never recurses more than a step or two deep whatever the chain length.

This was not always true. Resolution used to expand from the roots downwards, so
a long chain recursed its whole length and raised ``RecursionError`` somewhere
past 400. It also depended on the order you happened to register things in —
registering children before parents attached every node directly to the root and
hid the problem completely, which is exactly what an early benchmark here did.
Both orders are now tested.

=============================================
Things that are *not* the bottleneck
=============================================

Measured, then left alone:

- **Container dependencies are cheaper than scalar ones.** 160 parents with one
  ``list[RegistrationKey]`` field of ten members resolve in 31 ms; the same graph
  spelled as ten separate key fields takes 68 ms. ``list`` and ``dict`` were
  added for expressiveness and happen to be more than twice as fast.
- **Defining configuration classes costs more than resolving them.** A
  ``Configuration`` subclass costs about 0.32 ms to define, half of which is
  plain pydantic building its validator. 500 distinct configuration *classes*
  therefore cost ~160 ms to import, against ~17 ms to resolve. The import is the
  bill, and most of it is not cinnamon's.
- **Parallel resolution does not help.** Resolution is bound by the interpreter
  lock, not by anything a thread pool improves; measured at **0.84×** — slower
  than doing it serially.
