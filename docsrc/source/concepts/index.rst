.. _concepts:

Concepts
*********************************************

Four ideas hold the library up. A **configuration** declares typed parameters, a
**component** is the plain class those parameters are handed to, a
**registration** binds the two under a key, and a **dependency** lets one
registration point at another.

.. mermaid::

    flowchart LR
        C["Configuration<br/>typed parameters"]
        K["RegistrationKey<br/>name, tags, namespace"]
        P["component path<br/>'mypkg.models.SVC'"]
        R["Registry"]
        O["built component<br/>parameters passed in"]

        C --> K
        P --> K
        K --> R
        R --> O
        K -. "a field may hold another key" .-> C

Read them in order. Each page assumes the one before it.

.. list-table::
    :header-rows: 1
    :widths: 25 75

    * - Page
      - What it covers
    * - :doc:`configuration`
      - ``Param``, type constraints, conditions, variants, nesting
    * - :doc:`component`
      - how parameters and dependencies reach a plain class, and what a built one remembers
    * - :doc:`registration`
      - ``RegistrationKey``, the three ways to register, and the ``Registry`` API
    * - :doc:`dependencies`
      - keys as fields, children-first resolution, containers, external projects

If you have not run anything yet, :doc:`../quickstart` is shorter and gets you to
working code first.

.. toctree::
    :maxdepth: 2
    :hidden:

    configuration
    component
    registration
    dependencies
