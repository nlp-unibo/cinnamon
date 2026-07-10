.. _model:

Defining a SVM classifier
*************************************

We are ready to define our SVM classifier.

We define the ``SVCModel`` component to wrap  a SVC from sklearn.

Then, we define its associated ``SVCModelConfig`` and perform registrations.

Lastly, we define the runnable script to run our ``SVCModel``.

------------------
``SVCModel``
------------------

.. code-block:: python

    class SVCModel(Component):

        def __init__(
                self,
                C: float,
                kernel: str,
                class_weight: Optional[str] = 'balanced'
        ):
            self.C = C
            self.kernel = kernel
            self.class_weight = class_weight

            self.model = SVC(C=self.C,
                             kernel=self.kernel,
                             class_weight=self.class_weight)

        def fit(
                self,
                x_train: Any,
                y_train: Any,
                x_val: Optional[Any] = None,
                y_val: Optional[Any] = None,
        ) -> Tuple[Dict[str, float], Optional[Dict[str, float]]]:
            self.model.fit(X=x_train, y=y_train)
            train_info = self.evaluate(x=x_train, y=y_train)

            if x_val is not None:
                val_info = self.evaluate(x=x_val, y=y_val)
                return train_info, val_info

            return train_info, None

        def evaluate(
                self,
                x: Any,
                y: Any
        ) -> Dict[str, float]:
            predictions = self.predict(x=x)
            f1 = f1_score(y_pred=predictions, y_true=y).item()
            acc = accuracy_score(y_pred=predictions, y_true=y)

            return {
                'f1': f1,
                'acc': acc
            }

        def predict(
                self,
                x: Any
        ) -> Any:
            return self.model.predict(X=x)


Note how ``fit()`` and ``predict()`` functions simply wrap the ``model.fit()`` and ``model.predict()`` functions of the SVC.

-----------------------
``SVCModelConfig``
-----------------------

The ``SVCModel`` uses ``SVCModelConfig`` as default configuration template.

.. code-block:: python

    class SVCModelConfig(Configuration):

        @classmethod
        @register_method(name='model',
                         tags={'svc'},
                         namespace='examples',
                         component_class=SVCModel)
        def default(
                cls
        ):
            config = super().default()

            config.add(name='C',
                       value=1.0,
                       type_hint=float,
                       description='C parameter of SVC')
            config.add(name='kernel',
                       type_hint=str,
                       value='linear',
                       description='The kernel of the SVC')
            config.add(name='class_weight',
                       type_hint=Optional[str],
                       value='balanced',
                       description='The weighting technique for addressing class imbalance.'
                                   'Each sample in the training set receives a weight based on'
                                   ' its class distribution')

            return config

We register the ``SVCModelConfig`` via ``RegistrationKey`` (``name=model``, ``tags={'svc'}``, ``namespace=examples``) and bind it to ``SVCModel``.

----------------
Next!
----------------

That's it! We have defined our SVM classifier as a ``Component`` and its corresponding ``Configuration``.

Next, we define a proper evaluation criteria by wrapping our data, processing, and model pipeline into a ``Benchmark``.