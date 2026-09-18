.. _examples:

Worked pipeline
*********************************************

This section walks through a complete machine-learning pipeline, end to end.

It performs binary sentiment analysis on the `IMDB dataset
<https://ai.stanford.edu/~amaas/data/sentiment/>`_ using a Support Vector Machine.
Each stage — data loading, preprocessing, modelling, and evaluation — is a separate
component and configuration, wired together by the ``Registry``.

.. mermaid::

    flowchart LR
        L["IMDBLoader<br/>data_loader[imdb]"]
        T["TfIdfProcessor<br/>processor[tf-idf]"]
        E["LabelProcessor<br/>processor[label]"]
        M["SVCModel<br/>model[svc]"]
        B["SVCBenchmark<br/>benchmark[svc]"]
        B --> L
        B --> T
        B --> E
        B --> M

The benchmark holds the four keys and builds each child when ``run()`` needs it.
Every arrow is a dependency field, so ``cmn-check`` reports a typo in any of them
before anything is loaded.

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
   :hidden:

   Overview <overview.rst>
   Data Loader <data_loader.rst>
   Processor <processor.rst>
   Model <model.rst>
   Benchmark <benchmark.rst>
   Catalog <catalog.rst>
