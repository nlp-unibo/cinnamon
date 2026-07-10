.. _component:

Component
*********************************************

A ``Component`` is any class that implements some program logic — data loading,
model training, preprocessing, evaluation, and so on.

Cinnamon does not impose any particular API on your existing code, except that the
class must inherit from ``Component``:

.. code-block:: python

    from cinnamon.component import Component

    class DataLoader(Component):

        def __init__(self, df_path: str):
            self.df_path = df_path

        def load(self):
            ...

The same applies to more complex classes — the inheritance is the only required change.


=============================================
Receiving configuration parameters
=============================================

When the ``Registry`` builds a ``Component``, it unpacks the bound ``Configuration``'s
``values`` dictionary directly into the component's constructor:

.. code-block:: python

    component = ComponentClass(**config.values, **build_args)

This means that your component's ``__init__`` parameters must match the field names
of its bound ``Configuration``:

.. code-block:: python

    from pathlib import Path
    from cinnamon.configuration import Configuration, Param
    from cinnamon.component import Component

    class DataLoaderConfig(Configuration):
        df_path: Path = Param('path/to/data')
        batch_size: int = Param(32)

    class DataLoader(Component):

        def __init__(self, df_path: Path, batch_size: int):
            self.df_path = df_path
            self.batch_size = batch_size

You can also call a component directly from a configuration instance, without going
through the ``Registry``:

.. code-block:: python

    config = DataLoaderConfig.default()
    loader = DataLoader(**config.values)


=============================================
Nested configurations
=============================================

When a ``Configuration`` has a dependency field (a ``RegistrationKey`` pointing to
another ``Configuration``), the ``Registry`` resolves it to a ``Configuration``
instance before building the component.

The component therefore receives a ``Configuration`` object for that parameter,
not a primitive value:

.. code-block:: python

    from cinnamon.configuration import Configuration, Param
    from cinnamon.registry import RegistrationKey
    from cinnamon.component import Component

    class ProcessorConfig(Configuration):
        vocab_size: int = Param(30000)

    class DataLoaderConfig(Configuration):
        df_path: Path = Param('path/to/data')
        processor: RegistrationKey = Param(
            RegistrationKey(name='processor', tags={'default'}, namespace='nlp')
        )

    class DataLoader(Component):

        def __init__(self, df_path: Path, processor: ProcessorConfig):
            self.df_path = df_path
            self.processor = processor   # receives a ProcessorConfig instance

.. note::
    See `dependencies <https://nlp-unibo.github.io/cinnamon/dependencies.html>`_ for
    a full explanation of how nested configurations are declared and resolved.


=============================================
Building a component
=============================================

Once ``Registry.build()`` has been called, a component instance can be constructed
in two equivalent ways.

Via the ``Registry`` directly:

.. code-block:: python

    from cinnamon.registry import Registry

    loader = Registry.instantiate_component(
        name='data_loader',
        tags={'default'},
        namespace='showcasing'
    )

Via the ``Component`` class itself (syntactic sugar that also type-checks the result):

.. code-block:: python

    loader = DataLoader.instantiate(
        name='data_loader',
        tags={'default'},
        namespace='showcasing'
    )

``DataLoader.instantiate()`` raises a ``RuntimeError`` if the built instance is not
actually a ``DataLoader``. ``Registry.instantiate_component()`` skips that check but
is otherwise identical.

Both methods accept additional keyword arguments via ``**build_args``, which are merged
into ``config.values`` at build time and can be used to override specific parameters:

.. code-block:: python

    loader = DataLoader.instantiate(
        name='data_loader',
        tags={'default'},
        namespace='showcasing',
        batch_size=64       # overrides the registered default of 32
    )

.. note::
    ``build_args`` only override values at instantiation time — the registered
    ``Configuration`` stored in the ``Registry`` is not modified.


.. toctree::
   :maxdepth: 4
   :hidden:
   :caption: Contents:
   :titlesonly: