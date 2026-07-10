.. _catalog:

Available ``Configuration``
*************************************

Currently, ``cinnamon-examples`` provides the following registered ``Configuration``.

-------------
Data Loader
-------------

- ``name='data_loader', tags={'imdb'}, namespace='examples'``: the default ``IMDBLoader``.

------------
Processor
------------

- ``name='processor', tags={'tf-idf'}, namespace='examples'``: the default ``TfIdfProcessor``.
- ``name='processor', tags={'label'}, namespace='examples'``: the default ``LabelProcessor``.

-------------
Model
-------------

- ``name='model', tags={'svc'}, namespace='examples'``: the default ``SVCModel``.


-----------
Benchmark
-----------

- ``name='benchmark', tags={'svc'}, namespace='examples'``: the ``Benchmark`` that evaluates ``SVCModel`` on the IMDB dataset.
