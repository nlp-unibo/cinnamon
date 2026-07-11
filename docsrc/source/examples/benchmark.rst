.. _benchmark:

Benchmark
*************************************

``SVCBenchmark`` ties together the data loader, processors, and model into a single
runnable pipeline.

=============================================
``SVCBenchmark``
=============================================

.. code-block:: python

    class SVCBenchmark(Component):

        def __init__(
            self,
            data_loader: RegistrationKey,
            model: RegistrationKey,
            text_processor: RegistrationKey,
            label_processor: RegistrationKey,
        ):
            self.data_loader    = data_loader
            self.model          = model
            self.text_processor = text_processor
            self.label_processor = label_processor

        def run(self):
            logging.basicConfig(level=logging.INFO)

            data_loader = IMDBLoader.instantiate(self.data_loader)
            train_df, val_df, test_df = data_loader.get_splits()

            text_processor  = TfIdfProcessor.instantiate(self.text_processor)
            label_processor = LabelProcessor.instantiate(self.label_processor)

            x_train = text_processor.process(data=train_df, is_training_data=True)
            y_train = label_processor.process(data=train_df, is_training_data=True)
            x_val   = text_processor.process(data=val_df)
            y_val   = label_processor.process(data=val_df)
            x_test  = text_processor.process(data=test_df)
            y_test  = label_processor.process(data=test_df)

            model = SVCModel.instantiate(self.model)
            train_info, val_info = model.fit(
                x_train=x_train, y_train=y_train,
                x_val=x_val,     y_val=y_val
            )
            test_info = model.evaluate(x=x_test, y=y_test)

            logging.info(f'Train info:\n{train_info}')
            logging.info(f'Val info:\n{val_info}')
            logging.info(f'Test info:\n{test_info}')

Notice that ``SVCBenchmark.__init__`` receives ``RegistrationKey`` objects, not built
component instances. Each dependency is built lazily inside ``run()`` via
``Component.instantiate(key)``.

This is a deliberate design choice enabled by ``resolve_automatically=False`` in the
benchmark's registration (see below). It means:

- The ``Registry`` validates that each ``RegistrationKey`` exists and is resolvable,
  but does not build the nested components eagerly.
- Components are constructed only when ``run()`` is called, keeping memory usage low
  until the pipeline actually starts.
- Each nested component gets its own fresh instance per run, with no shared state.

=============================================
``SVCBenchmarkConfig``
=============================================

.. code-block:: python

    class SVCBenchmarkConfig(Configuration):
        data_loader: RegistrationKey = Param(
            RegistrationKey(name='data_loader', tags={'imdb'}, namespace='examples'),
            description='Data loader'
        )
        text_processor: RegistrationKey = Param(
            RegistrationKey(name='processor', tags={'tf-idf'}, namespace='examples'),
            description='Text processor'
        )
        label_processor: RegistrationKey = Param(
            RegistrationKey(name='processor', tags={'label'}, namespace='examples'),
            description='Label processor'
        )
        model: RegistrationKey = Param(
            RegistrationKey(name='model', tags={'svc'}, namespace='examples'),
            description='Classifier model'
        )

        @classmethod
        @register_method(
            name='benchmark',
            tags={'svc'},
            namespace='examples',
            component='examples.components.benchmark.SVCBenchmark',
            run_method='run',
            resolve_automatically=False      # keep RegistrationKey fields unresolved
        )
        def default(cls) -> 'SVCBenchmarkConfig':
            return super().default()

The four ``RegistrationKey`` fields point to the other registered components.
``resolve_automatically=False`` tells the ``Registry`` not to replace those keys with
``Configuration`` instances during ``dag_resolution()`` — they are passed as-is to
``SVCBenchmark.__init__``, which then resolves them lazily inside ``run()``.

The default keys can be swapped by overriding individual fields via ``model_copy()``:

.. code-block:: python

    # Use a custom model instead of the default SVC
    config = SVCBenchmarkConfig.default()
    config = config.model_copy(update={
        'model': RegistrationKey(name='model', tags={'custom'}, namespace='my_project')
    })

=============================================
Demo script
=============================================

.. code-block:: python

    from pathlib import Path
    from cinnamon.registry import Registry
    from examples.components.benchmark import SVCBenchmark

    if __name__ == '__main__':
        directory = Path(__file__).parent.parent.resolve()
        Registry.build(directory=directory)

        benchmark = SVCBenchmark.instantiate(
            name='benchmark', tags={'svc'}, namespace='examples'
        )
        benchmark.run()

``Registry.build()`` discovers and registers all four component configurations.
``SVCBenchmark.instantiate()`` builds the benchmark with its four ``RegistrationKey``
fields intact. ``benchmark.run()`` then builds and runs each nested component in sequence.

.. note::
    The demo is at ``examples/demos/demo_benchmark.py``.
    Run it from the ``examples/`` directory so that relative paths in
    ``IMDBLoaderConfig`` (the ``datasets/`` subfolder) resolve correctly.

=============================================
Congratulations!
=============================================

That's the full pipeline — a customisable, plug-and-play machine-learning experiment
where every stage can be swapped independently via ``RegistrationKey``.

To extend it, you can:

- Register a new ``model`` key pointing to a different classifier.
- Register a new ``processor`` key with different tf-idf parameters.
- Build a ``CustomBenchmarkConfig`` that mixes example and custom components.

See the `catalog <catalog.html>`_ for the full list of registered keys.