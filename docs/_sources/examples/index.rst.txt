.. _examples:

Examples
*********************************************

This section walks through a complete machine-learning pipeline built with cinnamon.

The pipeline performs binary sentiment analysis on the `IMDB dataset
<https://ai.stanford.edu/~amaas/data/sentiment/>`_ using a Support Vector Machine.
Each stage — data loading, preprocessing, modelling, and evaluation — is defined as a
separate ``Component`` and ``Configuration``, wired together by the ``Registry``.

.. toctree::
   :maxdepth: 1

   Overview <overview.rst>
   Data Loader <data_loader.rst>
   Processor <processor.rst>
   Model <model.rst>
   Benchmark <benchmark.rst>
   Catalog <catalog.rst>