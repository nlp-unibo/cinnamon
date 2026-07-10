.. _benchmark:

Defining a ``Benchmark``
*************************************

We have defined each individual piece of our machine learning experiment.

We now need to define a code logic that uses all of them to train and evaluate our SVM classifier on the IMDB dataset.

-------------------------
``SVCBenchmark``
-------------------------

We define a ``Component`` that wraps up data loading, data processing, model definition, model training, and model evaluation.

.. code-block:: python

    class SVCBenchmark(RunnableComponent):

        def __init__(
                self,
                data_loader: IMDBLoader,
                model: SVCModel,
                text_processor: TfIdfProcessor,
                label_processor: LabelProcessor
        ):
            self.data_loader = data_loader
            self.model = model
            self.text_processor = text_processor
            self.label_processor = label_processor

        def run(
                self,
                config: Optional[cinnamon.configuration.Configuration] = None
        ):
            logging.basicConfig()

            train_df, val_df, test_df = self.data_loader.get_splits()

            x_train = self.text_processor.process(data=train_df, is_training_data=True)
            y_train = self.label_processor.process(data=train_df, is_training_data=True)

            x_val = self.text_processor.process(data=val_df)
            y_val = self.label_processor.process(data=val_df)

            x_test = self.text_processor.process(data=test_df)
            y_test = self.label_processor.process(data=test_df)

            train_info, val_info = self.model.fit(x_train=x_train, y_train=y_train,
                                                  x_val=x_val, y_val=y_val)
            test_info = self.model.evaluate(x=x_test, y=y_test)

            logging.info(f'Train info:\n{train_info}')
            logging.info(f'Val info:\n{val_info}')
            logging.info(f'Test info:\n{test_info}')

.. note::
    The ``__init__`` of ``SVCBenchmark`` takes built ``Component`` instances. This is automatically handled by cinnamon.
    If you want to work with ``RegistrationKey`` (e.g., some components require additional attributes to initialize), set ``build_recursively=False`` in ``register`` and ``register_method``.

-------------------------
``SVCBenchmarkConfig``
-------------------------

We then define the corresponding ``SVCBenchmarkConfig``.

Notice how this configuration is an example of **nested configuration** where some ``Param`` point to ``RegistrationKey``.

.. code-block:: python

    class SVCBenchmarkConfig(Configuration):

        @classmethod
        @register_method(name='benchmark',
                         tags={'svc'},
                         namespace='examples',
                         component_class=SVCBenchmark)
        def default(
                cls
        ):
            config = super().default()

            config.add(name='data_loader',
                       value=RegistrationKey(name='data_loader',
                                             tags={'imdb'},
                                             namespace='examples'))

            config.add(name='text_processor',
                       value=RegistrationKey(name='processor',
                                             tags={'tf-idf'},
                                             namespace='examples'))
            config.add(name='label_processor',
                       value=RegistrationKey(name='processor',
                                             tags={'label'},
                                             namespace='examples'))

            config.add(name='model',
                       value=RegistrationKey(name='model',
                                             tags={'svc'},
                                             namespace='examples'))

            return config

--------------------------------
Running ``SVCBenchmark``
--------------------------------

We can now write a script to test ``SVCBenchmark``.

.. code-block:: python

    from pathlib import Path

    from cinnamon.registry import Registry
    from components.benchmark import SVCBenchmark

    if __name__ == '__main__':
        """
        In this demo script, we retrieve and build our SVC pipeline.
        The pipeline covers data loading, data processing, and model evaluation.
        """

        directory = Path(__file__).parent.parent.resolve()
        Registry.setup(directory=directory)

        benchmark = SVCBenchmark.build_component(name='benchmark',
                                                 tags={'svc'},
                                                 namespace='examples')
        benchmark.run()

------------------
Congratulations!
------------------

That's it! We have successfully defined a **customizable**, **plug-and-play**, and **re-usable** machine-learning pipeline.

Feel free to play to download this repository and play with ``Component`` and ``Configuration``.

Cheers!