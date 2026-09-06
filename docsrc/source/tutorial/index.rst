.. _tutorial:

Tutorial
*********************************************

Seven steps, each one a runnable file under ``examples/tutorial/``. They need
nothing beyond cinnamon itself, and they are meant to be run rather than read:
change a value, run it again, see what moves.

.. code-block:: bash

    pip install cinnamon
    python examples/tutorial/01_configuration.py

Every file on the following pages is included from the repository rather than
copied into the prose, and the test suite executes each one on every commit. If a
page here disagrees with the code, the build is broken — which is the only way a
tutorial stays true.

=============================================
The idea, in one line
=============================================

**Components carry the weight. Configurations describe it.**

Components are where your logic lives. Configurations are the parameter sets you
run it with — lightweight, numerous, and quick to write, because the normal case
is running many experiments over *the same component*. Almost everything in the
seven steps follows from that split.

=============================================
The steps
=============================================

====================================  ==================================================
Page                                  Introduces
====================================  ==================================================
:doc:`configuration`                  ``Configuration``, ``Param``, validation
:doc:`registration`                   components as plain classes, ``RegistrationKey``
:doc:`variants`                       one component, many configurations
:doc:`dependencies`                   configurations that reference other registrations
:doc:`collections`                    ``list`` and ``dict`` of keys
:doc:`conditions`                     conditions, and the valid/invalid split
:doc:`project_layout`                 the real directory layout and the CLI
====================================  ==================================================

Steps 1–6 register everything by hand in a single file, so each concept stays
readable in one screen. That is a teaching device: real projects use the directory
layout in step 7 and never call ``Registry.register_configuration`` directly.

For the same reason, steps 1–6 bind components with ``f"{__name__}.ClassName"``,
which resolves to ``__main__`` in a script. A real project writes
``"mypackage.components.Tokenizer"``.

=============================================
A note on what is *not* here
=============================================

``arbitrary_types_allowed``. A configuration that holds a live model or database
connection compiles fine and quietly erases the distinction the library is built
on, so cinnamon refuses the field and explains why. :doc:`configuration` has a
commented-out example if you want to see the message.

.. toctree::
   :maxdepth: 1
   :hidden:

   1. Configuration <configuration.rst>
   2. Registration <registration.rst>
   3. Variants <variants.rst>
   4. Dependencies <dependencies.rst>
   5. Collections <collections.rst>
   6. Conditions <conditions.rst>
   7. A real project <project_layout.rst>
