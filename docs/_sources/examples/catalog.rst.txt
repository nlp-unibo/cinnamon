.. _catalog:

Registered Keys
*************************************

All keys registered by the examples project under the ``examples`` namespace.

=============================================
Data Loader
=============================================

``name='data_loader', tags={'imdb'}, namespace='examples'``
    Downloads, extracts, and parses the IMDB dataset into a ``pandas.DataFrame``.
    Bound to ``IMDBLoader``. ``run_method='load_data'``.

=============================================
Processors
=============================================

``name='processor', tags={'tf-idf'}, namespace='examples'``
    Converts raw text into a sparse tf-idf matrix using ``TfidfVectorizer``.
    Bound to ``TfIdfProcessor``.

``name='processor', tags={'label'}, namespace='examples'``
    Encodes string labels (``'pos'``, ``'neg'``) into integers using ``LabelEncoder``.
    Bound to ``LabelProcessor``. Uses the base ``Configuration`` (no fields).

=============================================
Model
=============================================

``name='model', tags={'svc'}, namespace='examples'``
    A linear SVC classifier with ``C=1.0`` and ``class_weight='balanced'``.
    Bound to ``SVCModel``.

=============================================
Benchmark
=============================================

``name='benchmark', tags={'svc'}, namespace='examples'``
    The full pipeline: loads IMDB data, applies tf-idf and label processing,
    trains and evaluates the SVC. Bound to ``SVCBenchmark``. ``run_method='run'``.
    ``resolve_automatically=False`` — dependency keys are kept as ``RegistrationKey``
    objects and resolved lazily inside ``SVCBenchmark.run()``.