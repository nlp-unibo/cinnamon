.. _tutorial_project_layout:

7. A real project
*********************************************

Steps 1–6 registered everything by hand in a single file so each concept stayed
readable in one screen. Real projects do not do that. They put registrations in a
``configurations/`` package, let ``Registry.build`` discover them, and drive the
whole thing from the command line.

.. code-block:: text

    examples/tutorial/07_project_layout/
    ├── components/
    │   ├── __init__.py
    │   └── summariser.py       # the logic: plain classes
    └── configurations/
        ├── __init__.py
        └── summariser.py       # the registrations

``Registry.build`` finds every ``configurations/`` package beneath the directory it
is given, imports the modules inside, and runs whatever the ``@register`` and
``@register_method`` decorators buffered. ``components/`` is a convention, not a
requirement — a component is found by the import path its registration names.

===============================================
The registrations
===============================================

.. literalinclude:: ../../../examples/tutorial/07_project_layout/configurations/summariser.py
   :language: python
   :linenos:

Two entry points appear here, and they are equivalent:

- ``@register_method`` decorates a ``default()`` classmethod on the configuration.
  Concise when the registration belongs naturally to the class.
- ``@register`` decorates a plain function that registers whatever it likes. Use it
  when a ``default()`` classmethod would be contrived, or to register a
  configuration you did not write.

``run_method="run"`` is what makes a registration discoverable by ``cmn-run``.

===============================================
The components
===============================================

.. literalinclude:: ../../../examples/tutorial/07_project_layout/components/summariser.py
   :language: python
   :linenos:

===============================================
Driving it from the command line
===============================================

.. code-block:: bash

    cd examples/tutorial/07_project_layout

    cmn-check -dir .          # look for mistakes before running anything
    cmn-build -dir .          # resolve, and write the key list to registrations/
    cmn-run   -dir .          # pick a configuration interactively and run it

``cmn-check`` and ``cmn-build`` need only ``pip install cinnamon``. ``cmn-run``
prompts, so it also wants ``pip install "cinnamon[cli]"``. :doc:`../commands`
covers all four commands in detail.

Four registrations come out of two declarations, because the strategy declares a
variant and the summariser inherits it:

.. code-block:: text

    strategy--tags=['truncate']
    strategy--tags=['sentences=2', 'truncate']
    summariser
    summariser--tags=['strategy.sentences=2', 'strategy.truncate']

That last key is worth a second look: it records *which* strategy the summariser
was built against. Nobody wrote it down — resolution derived it, and it will be the
same key on the next machine and in six months.

===============================================
After the tutorial
===============================================

- :doc:`../examples/index` — a full scikit-learn pipeline: loader, processors,
  model, benchmark. Needs ``pip install "cinnamon[examples]"`` and downloads the
  IMDB dataset on first run.
- :doc:`../configuration`, :doc:`../component`, :doc:`../registration` and
  :doc:`../dependencies` cover each concept in depth.
- `CONTRIBUTING.md <https://github.com/nlp-unibo/cinnamon/blob/main/CONTRIBUTING.md>`_
  — the design principle in more depth, and how to work on cinnamon itself.
