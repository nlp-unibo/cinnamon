.. _tutorial_registration:

2. Registration
*********************************************

A component is an ordinary class — no base class, no decorator. cinnamon needs only
its *import path*, as a string, which it resolves when you ask for an instance and
not before.

.. code-block:: bash

    python examples/tutorial/02_registration.py

That is what keeps a build independent of how heavy your components are: nothing
imports torch to look at a registry.

.. literalinclude:: ../../../examples/tutorial/02_registration.py
   :language: python
   :pyobject: Tokenizer

A registration binds ``(configuration, name, namespace, tags)`` to that component
path. A ``RegistrationKey`` — name, namespace, and a set of tags — is how you name
the binding afterwards, and how you ask for the component.

===============================================
What to notice
===============================================

- ``Registry.dag_resolution()`` returns *two* sets, valid and invalid. Step 6
  explains why the second one is not an error list.
- ``Registry.from_key`` is the moment the component class is imported. Before it,
  the registry knows the path and nothing more.
- ``Registry.retrieve_configuration`` gets the configuration back without building
  anything at all.

===============================================
The whole file
===============================================

.. literalinclude:: ../../../examples/tutorial/02_registration.py
   :language: python
   :linenos:

Next: :doc:`variants` — the reason the library exists.
