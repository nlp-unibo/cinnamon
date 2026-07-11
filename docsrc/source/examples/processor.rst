.. _processor:

Processors
*************************************

Before training the SVM classifier, the raw text and labels need to be
converted into numerical form. Two processor components handle this.

=============================================
``TfIdfProcessor``
=============================================

``TfIdfProcessor`` wraps scikit-learn's ``TfidfVectorizer`` to convert raw text
into a sparse tf-idf matrix:

.. code-block:: python

    class TfIdfProcessor(Component):

        def __init__(self, **kwargs):
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

The ``**kwargs`` constructor accepts any ``TfidfVectorizer`` parameter.
Configuration fields are forwarded directly since ``config.values`` unpacks into
``TfIdfProcessor(**config.values)``.

``TfIdfProcessorConfig`` exposes ``ngram_range`` as the primary configurable parameter:

.. code-block:: python

    class TfIdfProcessorConfig(Configuration):
        ngram_range: Tuple[int, int] = Param(
            (1, 1),
            description='Vectorizer ngram_range hyper-parameter'
        )

        @classmethod
        @register_method(
            name='processor',
            tags={'tf-idf'},
            namespace='examples',
            component='examples.components.processor.TfIdfProcessor'
        )
        def default(cls) -> 'TfIdfProcessorConfig':
            return super().default()

=============================================
``LabelProcessor``
=============================================

``LabelProcessor`` wraps scikit-learn's ``LabelEncoder`` to convert string labels
(``'pos'``, ``'neg'``) into integers:

.. code-block:: python

    class LabelProcessor(Component):

        def __init__(self):
            self.label_encoder = LabelEncoder()

        def process(
            self,
            data: Optional[pd.DataFrame],
            is_training_data: bool = False,
        ) -> Optional[Any]:
            if data is None:
                return data
            labels = data.y.values
            if is_training_data:
                self.label_encoder.fit(labels)
            return self.label_encoder.transform(labels)

``LabelProcessor`` takes no constructor parameters, so it can be bound directly to
the base ``Configuration`` without defining a custom subclass:

.. code-block:: python

    @register
    def register_processors():
        Registry.register_configuration(
            config=Configuration.default(),
            component='examples.components.processor.LabelProcessor',
            name='processor',
            tags={'label'},
            namespace='examples'
        )

The ``@register`` decorator marks this function for automatic discovery by
``Registry.build()``. The base ``Configuration.default()`` produces an empty
configuration with no fields, which is all ``LabelProcessor`` needs.