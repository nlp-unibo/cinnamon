.. _tutorial_configuration:

1. Configuration
*********************************************

A configuration is a typed, documented parameter set. Nothing is registered yet —
this step is only about what a ``Configuration`` *is*, because everything later is
built on it.

.. code-block:: bash

    python examples/tutorial/01_configuration.py

Fields are declared as annotated class attributes wrapped in ``Param``, which is a
pydantic ``Field`` with a little extra: a description that stays attached, and the
``variants`` that step 3 uses.

.. literalinclude:: ../../../examples/tutorial/01_configuration.py
   :language: python
   :pyobject: TokenizerConfig

Constraints are pydantic's, and they are enforced when the value is *set* rather
than when it is used, so an impossible configuration never reaches a component.

===============================================
What to notice
===============================================

- ``config.values`` gives a plain ``{field: value}`` dictionary. That is what gets
  unpacked into the component's ``__init__``, and it is why a component never needs
  to know cinnamon exists.
- Descriptions are not comments. They survive into ``model_fields``, so a
  configuration documents itself and the CLI can read them back.
- The end of the file has a commented-out field holding a ``sqlite3.Connection``.
  Uncomment it and run again: cinnamon refuses it and explains why. A configuration
  holding a live object has stopped describing a component and started being one.

===============================================
The whole file
===============================================

.. literalinclude:: ../../../examples/tutorial/01_configuration.py
   :language: python
   :linenos:

Next: :doc:`registration` binds a configuration to a component.
