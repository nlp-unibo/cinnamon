.. _overview:

Cinnamon
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

    pip install cinnamon-core

.. note::
    The distribution is ``cinnamon-core``; the import package is ``cinnamon``.
    You install ``cinnamon-core`` and then write ``import cinnamon``.

    They differ because ``cinnamon`` on PyPI is an unrelated project.
    ``cinnamon-core`` is the package these releases have always used, and it
    supersedes the old ``cinnamon-generic`` / ``cinnamon-th`` / ``cinnamon-tf``
    split.

That is everything the library needs, and everything ``cmn-build`` and
``cmn-check`` need. The two commands that *prompt* — ``cmn-run`` and
``cmn-generate`` — also want a terminal-UI library:

.. code-block:: bash

    pip install "cinnamon-core[cli]"

From source:

.. code-block:: bash

    git clone https://github.com/nlp-unibo/cinnamon
    pip install ./cinnamon

===============================================
Where to start
===============================================

:doc:`quickstart` walks through a first configuration, component and registration
in a few minutes. It is the shortest path from here to running code.

The :doc:`tutorial <tutorial/index>` is seven runnable files that build the library
up one idea at a time — configuration, registration, variants, dependencies,
collections, conditions, and a worked project with the real directory layout.
Every one of them is executed by the test suite, so what you read is what runs.

Then :doc:`configuration`, :doc:`component`, :doc:`registration` and
:doc:`dependencies` cover each concept properly, :doc:`commands` covers the command
line, and :doc:`examples/index` works through a complete scikit-learn pipeline.

===============================================
Contact
===============================================

Don't hesitate to contact:

- `Federico Ruggeri <https://federicoruggeri.github.io>`_

for questions/doubts/issues!

.. toctree::
   :maxdepth: 4
   :hidden:
   :caption: Getting started:
   :titlesonly:

   Quickstart <quickstart.rst>

.. toctree::
   :maxdepth: 2
   :hidden:
   :caption: Tutorial:
   :titlesonly:

   Tutorial <tutorial/index.rst>

.. toctree::
   :maxdepth: 4
   :hidden:
   :caption: Concepts:
   :titlesonly:

   Configuration <configuration.rst>
   Component <component.rst>
   Registration <registration.rst>
   Dependencies <dependencies.rst>

.. toctree::
   :maxdepth: 4
   :hidden:
   :caption: Reference:
   :titlesonly:

   Commands <commands.rst>
   Code Documentation <modules.rst>

.. toctree::
   :maxdepth: 1
   :hidden:
   :caption: Examples:
   :titlesonly:

   Worked pipeline <examples/index.rst>
