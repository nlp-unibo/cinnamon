.. _overview:

Quickstart
=============================================

This project contains a complete example of a machine-learning pipeline.

In particular, we'll see how

- Define a ``DataLoader``
- Define two data ``Processor``, one for tf-idf features and one for one-hot label encoding
- Define a SVM classifier ``Model``
- Train and evaluate our classifier with a ``Benchmark``

We consider the IMDB data to perform a binary classification for sentiment analysis.

===============================================
Usage
===============================================

Want to use the ``Component`` and ``Configuration`` of this example project?

You can quickly integrate them into your project by cloning this Github repo and add it to ``Registry.setup()``.

.. code-block:: python

   Registry.build(directory=...,
                  external_directories=[
                      "path/where/cinnamon_examples/is/stored",
                  ])


Done! Cinnamon will automatically import all registered ``Configuration`` under `configurations` folders.

.. note::
   Remember to first install all requirements to allow successful code import.

We then can define any registration that uses ``Component`` or ``Configuration`` declared in this repo.

.. code-block:: python

    @register(name='model', tags={'custom'}, namespace='my_own')
    def register_custom_model_config():
        config = SVCModelConfig.default()

        config.C = 0.5
        config.kernel = 'rbf'

        return config

Or that we want to re-use ``IMBDLoader`` with our custom benchmark.

.. code-block:: python

    class CustomBenchmarkConfig(Configuration):

     @classmethod
     @register_method(name='benchmark', tags={'custom'}, namespace='my_own')
     def default(cls):
         config = super(cls).default()

         config.add(name='data_loader',
                    value=RegistrationKey(name='data_loader',
                                      tags={'imdb'},
                                      namespace='examples'))

         config.add(name='model',
                    value=RegistrationKey(name='model',
                                          tags={'imdb', 'lstm'},
                                          namespace='my_own'))

         ...

         return config

===============================================
Contact
===============================================

Don't hesitate to contact:

- `Federico Ruggeri <https://www.unibo.it/sitoweb/federico.ruggeri6/en>`_

for questions/doubts/issues!
