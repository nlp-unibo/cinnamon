.. _overview:

Overview
*********************************************

**Components carry the weight. Configurations describe it.**

That sentence is most of cinnamon. Everything else follows from it, and the parts
of the API that look odd at first usually make sense once it is in mind.

- A **component** is where your logic lives — a data loader, a model, an evaluation
  pipeline. It is an ordinary Python class. cinnamon asks nothing of it: no base
  class, no decorator, no import.
- A **configuration** describes the parameters that component runs with. It is
  lightweight, and there are usually many of them, because the interesting question
  is rarely "what does this do?" but "what does it do with *these* settings?".

The motivating case is research — running the same model over a grid of
hyper-parameters, and being able to say afterwards exactly which combination
produced which number. The shape generalises to anything with expensive reusable
logic and a large space of choices.

===============================================
What that buys you
===============================================

**Sweeps you declare rather than script.** Say a field has variants and cinnamon
enumerates the combinations, giving each one a key derived from its values:

.. code-block:: python

    class ClassifierConfig(Configuration):
        learning_rate: float = Param(1e-3, variants=[1e-2, 1e-4])
        hidden_size: int = Param(128, variants=[256])

    # six configurations, each addressable as
    #   classifier--tags=['hidden_size=256', 'learning_rate=0.01']

Those keys are derived, not written down, and they are stable across runs and
machines. That is what makes a result reproducible: the key *is* the description of
the experiment.

**Composition without wiring.** A configuration can depend on another by key. When
a child has variants, the parent gains one configuration per child variant —
sweeps compose down the graph without anyone joining them up.

**Mistakes caught before anything runs.** ``cmn-check`` reports unresolved keys with
suggestions, and checks that components match the configurations bound to them —
all without importing your components.

**Nothing imported until it is needed.** A component is bound by its import path as
a string, so building a registry never imports torch. On a project whose components
take 650 ms to import, the registry builds in 8 ms.

===============================================
Install
===============================================

.. code-block:: bash

    pip install cinnamon              # core
    pip install "cinnamon[cli]"       # adds cmn-run and cmn-generate

From source:

.. code-block:: bash

    git clone https://github.com/nlp-unibo/cinnamon
    pip install ./cinnamon

===============================================
Where to start
===============================================

:doc:`quickstart` walks through a first configuration, component and registration.

The **tutorial** in the repository is seven runnable files that need nothing beyond
cinnamon itself — configuration, registration, variants, dependencies, collections,
conditions, and a worked project with the real directory layout:

.. code-block:: bash

    python examples/tutorial/01_configuration.py

Then :doc:`configuration`, :doc:`component`, :doc:`registration` and
:doc:`dependencies` cover each concept properly, and :doc:`commands` covers the
command line.

===============================================
Contact
===============================================

Don't hesitate to contact:

- `Federico Ruggeri <https://federicoruggeri.github.io>`_

for questions/doubts/issues!

.. toctree::
   :maxdepth: 4
   :hidden:
   :caption: Contents:
   :titlesonly:
