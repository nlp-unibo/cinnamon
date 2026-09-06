.. _tutorial_collections:

5. Collections
*********************************************

A dependency field can hold a ``list`` of keys, or a ``dict`` of them keyed by
string. Use a list when order is what matters — a pipeline of stages, a set of loss
terms — and a dict when the members need names.

.. code-block:: bash

    python examples/tutorial/05_collections.py

.. literalinclude:: ../../../examples/tutorial/05_collections.py
   :language: python
   :pyobject: ModelConfig

The component receives the container of keys, in the shape it was declared with,
and ``Registry.from_keys`` builds the whole thing at once while keeping that shape.

.. literalinclude:: ../../../examples/tutorial/05_collections.py
   :language: python
   :pyobject: Model

===============================================
What to notice
===============================================

- **One level only.** ``list[list[RegistrationKey]]`` is refused, with an error that
  says so. Nesting would mean inventing a path language to address a key inside a
  container, and the graph would stop being a graph over keys.
- ``Optional[list[RegistrationKey]]`` and the parameterized
  ``RegistrationKey[Tokenizer]`` are both dependencies too.
- A container varies through variants declared on the **whole field** — 
  ``Param([a, b], variants=[[a], [a, b, c]])`` — not by its members varying
  individually. :doc:`../dependencies` explains why, and what the derived tag looks
  like.

===============================================
The whole file
===============================================

.. literalinclude:: ../../../examples/tutorial/05_collections.py
   :language: python
   :linenos:

Next: :doc:`conditions` — rejecting the combinations that make no sense.
