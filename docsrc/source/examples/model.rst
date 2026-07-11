.. _model:

SVM Classifier
*************************************

The model stage wraps scikit-learn's ``SVC`` as a cinnamon ``Component``.

=============================================
``SVCModel``
=============================================

.. code-block:: python

    class SVCModel(Component):

        def __init__(self, C: float, kernel: str, class_weight: Optional[str] = 'balanced'):
            self.C = C
            self.kernel = kernel
            self.class_weight = class_weight
            self.model = SVC(C=self.C, kernel=self.kernel, class_weight=self.class_weight)

        def fit(
            self,
            x_train, y_train,
            x_val=None, y_val=None,
        ) -> Tuple[Dict[str, float], Optional[Dict[str, float]]]:
            self.model.fit(X=x_train, y=y_train)
            train_info = self.evaluate(x=x_train, y=y_train)
            if x_val is not None:
                return train_info, self.evaluate(x=x_val, y=y_val)
            return train_info, None

        def evaluate(self, x, y) -> Dict[str, float]:
            predictions = self.predict(x=x)
            return {
                'f1':  f1_score(y_pred=predictions, y_true=y),
                'acc': accuracy_score(y_pred=predictions, y_true=y),
            }

        def predict(self, x) -> Any:
            return self.model.predict(X=x)

``fit()`` trains the SVC and returns evaluation metrics for both train and (optional)
validation sets. ``evaluate()`` returns ``f1`` and ``acc`` scores. ``predict()``
wraps ``model.predict()`` directly.

=============================================
``SVCModelConfig``
=============================================

.. code-block:: python

    class SVCModelConfig(Configuration):
        C: float = Param(1.0, description='Regularisation parameter of SVC')
        kernel: str = Param('linear', description='Kernel type')
        class_weight: str = Param(
            'balanced',
            description='Weighting strategy for class imbalance'
        )

        @classmethod
        @register_method(
            name='model',
            tags={'svc'},
            namespace='examples',
            component='examples.components.model.SVCModel'
        )
        def default(cls) -> 'SVCModelConfig':
            return super().default()

The three fields correspond exactly to the three parameters of ``SVCModel.__init__``.
When the ``Registry`` builds ``SVCModel``, it calls ``SVCModel(**config.values)``,
which unpacks ``{'C': 1.0, 'kernel': 'linear', 'class_weight': 'balanced'}``
directly into the constructor.