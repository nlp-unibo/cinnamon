.. _examples:

Worked pipeline
*********************************************

This section walks through a complete machine-learning pipeline, end to end.

It performs binary sentiment analysis on the `IMDB dataset
<https://ai.stanford.edu/~amaas/data/sentiment/>`_ using a Support Vector Machine.
Each stage — data loading, preprocessing, modelling, and evaluation — is a separate
component and configuration, wired together by the ``Registry``.

.. code-block:: bash

    pip install -e ".[examples]"
    python -m examples.demos.demo_benchmark

.. note::
    The dataset is downloaded on first run.

If you have not met the concepts yet, start with the :doc:`../tutorial/index`
instead: seven short runnable files that build them up one at a time, needing
nothing beyond cinnamon itself. This section assumes them.

.. toctree::
   :maxdepth: 1

   Overview <overview.rst>
   Data Loader <data_loader.rst>
   Processor <processor.rst>
   Model <model.rst>
   Benchmark <benchmark.rst>
   Catalog <catalog.rst>
