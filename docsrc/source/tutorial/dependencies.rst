.. _tutorial_dependencies:

4. Dependencies
*********************************************

A field typed as ``RegistrationKey`` is a dependency. cinnamon records it as an edge
in the dependency graph, so it knows what a pipeline is made of before anything is
built.

.. code-block:: bash

    python examples/tutorial/04_dependencies.py

.. literalinclude:: ../../../examples/tutorial/04_dependencies.py
   :language: python
   :pyobject: PipelineConfig

Note what the *component* receives: the key itself, not a built object. The
component decides when — and whether — to build its child.

.. literalinclude:: ../../../examples/tutorial/04_dependencies.py
   :language: python
   :pyobject: Pipeline

That laziness is deliberate, and it is also why a dependency can be swapped without
touching the parent's code.

===============================================
What to notice
===============================================

- **Sweeps compose down the graph.** ``TokenizerConfig`` declares a variant on
  ``lowercase``; the pipeline never mentions it, and yet resolution produces one
  pipeline configuration per tokenizer variant. The parent's key records which
  child it was built against, as a derived tag such as
  ``tokenizer.lowercase=False``.
- Nobody joined those up. The edge in the graph is enough.
- Because the child arrives as a key, a component can hold a dependency it never
  builds — a branch that only some configurations take.

===============================================
The whole file
===============================================

.. literalinclude:: ../../../examples/tutorial/04_dependencies.py
   :language: python
   :linenos:

Next: :doc:`collections` — depending on many registrations at once.
