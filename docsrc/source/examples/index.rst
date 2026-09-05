.. _examples:

Examples
*********************************************

=============================================
Tutorial
=============================================

The repository ships a tutorial under ``examples/tutorial/``: seven runnable files
that need nothing beyond cinnamon itself. Each is short enough to read in one
screen, and each is executed by the test suite, so what you read is what runs.

.. code-block:: bash

    pip install -e .
    python examples/tutorial/01_configuration.py

======  ============================================================
Step    Introduces
======  ============================================================
1       ``Configuration``, ``Param``, validation
2       components as plain classes, ``RegistrationKey``
3       **variants** — one component, many configurations
4       dependencies, and how sweeps compose down the graph
5       ``list`` and ``dict`` of keys, and ``Registry.from_keys``
6       conditions, and the valid/invalid split
7       a worked project: real layout, ``cmn-check`` / ``cmn-build`` / ``cmn-run``
======  ============================================================

Steps 1–6 register by hand in a single file so each concept stays readable; step 7
shows the directory layout a real project uses.

=============================================
A full pipeline
=============================================

The rest of this section walks through a complete machine-learning pipeline.

It performs binary sentiment analysis on the `IMDB dataset
<https://ai.stanford.edu/~amaas/data/sentiment/>`_ using a Support Vector Machine.
Each stage — data loading, preprocessing, modelling, and evaluation — is a separate
component and configuration, wired together by the ``Registry``.

.. code-block:: bash

    pip install -e ".[examples]"
    python -m examples.demos.demo_benchmark

.. note::
    The dataset is downloaded on first run.

.. toctree::
   :maxdepth: 1

   Overview <overview.rst>
   Data Loader <data_loader.rst>
   Processor <processor.rst>
   Model <model.rst>
   Benchmark <benchmark.rst>
   Catalog <catalog.rst>
