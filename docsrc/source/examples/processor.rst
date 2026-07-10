.. _processor:

Parsing data with ``Processor``
*************************************

We still need to parse loaded data in order to train and evaluate our SVM classifier.

We can define several plug-and-play ``Processor`` to

- Process input data
- Process classification labels
- Process data for the classifier

--------------------
Input data
--------------------

To process input data, we rely on tf-idf processing since we are dealing with a SVM classifier.

We define a ``TfIdfProcessor`` as follows

.. code-block:: python

    class TfIdfProcessor(Component):

        def __init__(
                self,
                **kwargs
        ):
            self.vectorizer = TfidfVectorizer(**kwargs)

        def process(
                self,
                data: Optional[pd.DataFrame],
                is_training_data: bool = False,
        ) -> Optional[Any]:
            if data is None:
                return data

            if is_training_data:
                self.vectorizer.fit(data.x.values)

            return self.vectorizer.transform(data.x.values)


The ``TfIdfProcessor`` has an internal ``TfidfVectorizer`` from sklearn. The vectorizer is used in ``process()`` to convert textual input data into numerical format.

We define a corresponding ``TfIdfProcessorConfig`` with minimal view (for simplicity) of the vectorizer.

.. code-block:: python

    class TfIdfProcessorConfig(Configuration):

        @classmethod
        @register_method(name='processor',
                         tags={'tf-idf'},
                         namespace='examples',
                         component_class=TfIdfProcessor)
        def default(
                cls
        ):
            config = super().default()

            config.add(name='ngram_range',
                       value=(1, 1),
                       type_hint=Any,
                       description='Vectorizer ngram_range hyper-parameter')

            return config


We register the ``TfIdfProcessorConfig`` via ``RegistrationKey`` (``name=processor``, ``tags={'tf-idf'}``, ``namespace=examples``) and bind it to ``TfIdfProcessor``.


-----------------------
Classification Labels
-----------------------

To process classification labels, we rely on one-hot encoding via ``LabelEncoder`` from sklearn.

We define a ``LabelProcessor`` as follows

.. code-block:: python

    class LabelProcessor(Component):

        def __init__(
                self
        ):
            self.label_encoder = LabelEncoder()

        def process(
                self,
                data: Optional[pd.DataFrame],
                is_training_data: bool = False
        ) -> Optional[Any]:
            if data is None:
                return data

            labels = data.y.values
            if is_training_data:
                self.label_encoder.fit(labels)

            return self.label_encoder.transform(labels)

The ``LabelProcessor`` doesn't require any specific configuration since it has no hyper-parameters.

Thus, we can bind it to ``Configuration``.

.. code-block:: python

    @register
    def register_processors():
        Registry.register_configuration(config_class=Configuration,
                                        component_class=LabelProcessor,
                                        name='processor',
                                        tags={'label'},
                                        namespace='examples')


----------------
Next!
----------------

That's it! We have defined processors to parse input data so that it can be digested by our SVM classifier.

Next, we define the SVM classifier as a custom ``Model`` component.