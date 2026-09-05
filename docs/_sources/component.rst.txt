.. _component:

Component
*********************************************

A component is any class that implements some program logic — data loading, model
training, preprocessing, evaluation, and so on. It is where the weight of your
program lives.

**cinnamon imposes nothing on it.** No base class, no decorator, no import:

.. code-block:: python

    class DataLoader:

        def __init__(self, df_path: str, batch_size: int):
            self.df_path = df_path
            self.batch_size = batch_size

        def load(self):
            ...

That is a complete, registrable component. Earlier versions of cinnamon required
inheriting from a ``Component`` base class; that class was removed, and nothing
replaced it.

=============================================
Receiving configuration parameters
=============================================

When the ``Registry`` builds a component, it unpacks the bound ``Configuration``'s
``values`` into the constructor:

.. code-block:: python

    component = ComponentClass(**config.values, **build_args)

So the component's ``__init__`` parameters must match the field names of its bound
``Configuration``:

.. code-block:: python

    from pathlib import Path
    from cinnamon.configuration import Configuration, Param

    class DataLoaderConfig(Configuration):
        df_path: Path = Param('path/to/data')
        batch_size: int = Param(32)

    class DataLoader:

        def __init__(self, df_path: Path, batch_size: int):
            self.df_path = df_path
            self.batch_size = batch_size

``cmn-check --deep`` verifies that correspondence for every registration, so a
renamed field is caught before you run anything.

You can also build a component straight from a configuration, without the registry:

.. code-block:: python

    config = DataLoaderConfig.default()
    loader = DataLoader(**config.values)

=============================================
Receiving dependencies
=============================================

A dependency field holds a :class:`~cinnamon.registry.RegistrationKey`, and **that
key is what the component receives** — not a resolved configuration, and not a
built object:

.. code-block:: python

    from cinnamon.configuration import Configuration, Param
    from cinnamon.registry import RegistrationKey, Registry

    class PipelineConfig(Configuration):
        processor: RegistrationKey = Param(
            RegistrationKey(name='processor', tags={'tf-idf'}, namespace='nlp')
        )

    class Pipeline:

        def __init__(self, processor: RegistrationKey):
            # The component builds its own child, when it wants to.
            self.processor = Registry.from_key(processor)

This is deliberate. Because the component holds a key rather than an instance, it
decides *when* — and *whether* — each child is built. A child that is only needed
on one code path costs nothing on the others, and a component can build the same
child twice if that is what it means to do.

For containers, :meth:`~cinnamon.registry.Registry.from_keys` does the same job
while keeping the shape:

.. code-block:: python

    class ModelConfig(Configuration):
        losses: list[RegistrationKey] = Param([...])
        metrics: dict[str, RegistrationKey] = Param({...})

    class Model:

        def __init__(self, losses, metrics):
            self.losses = Registry.from_keys(losses)     # list  -> list, in order
            self.metrics = Registry.from_keys(metrics)   # dict  -> dict, same labels

.. note::
    See :doc:`dependencies` for how dependencies are declared, resolved and varied.

=============================================
Binding a component to a configuration
=============================================

The binding is the component's **import path, as a string**:

.. code-block:: python

    Registry.register_configuration(
        config=DataLoaderConfig(),
        name='data_loader',
        namespace='nlp',
        component='mypackage.components.DataLoader',
    )

A string rather than the class itself, because the class is imported only when an
instance is actually requested. A registry can therefore be built — and inspected,
and checked for mistakes — without importing any of the components it names, which
matters when those components pull in torch or scikit-learn. Importing one such
library typically costs more than building an entire registry.

``cmn-check`` resolves these paths on the filesystem without importing anything;
``cmn-check --deep`` imports them to check signatures too.

=============================================
Building a component
=============================================

Once :meth:`~cinnamon.registry.Registry.build` has run:

.. code-block:: python

    from cinnamon.registry import RegistrationKey, Registry

    key = RegistrationKey(name='data_loader', tags={'default'}, namespace='nlp')
    loader = Registry.from_key(key)

:meth:`~cinnamon.registry.Registry.instantiate` is the same thing with the key
spelled out, and an optional type check:

.. code-block:: python

    loader = Registry.instantiate(
        name='data_loader',
        tags={'default'},
        namespace='nlp',
        expected_type=DataLoader,     # raises TypeError if it is not one
    )

Both accept extra keyword arguments, merged into ``config.values`` at build time:

.. code-block:: python

    loader = Registry.instantiate(
        name='data_loader',
        tags={'default'},
        namespace='nlp',
        batch_size=64,       # overrides the registered default of 32
    )

.. note::
    ``build_args`` override values for this build only — the ``Configuration``
    stored in the ``Registry`` is unchanged.

=============================================
Runnable components
=============================================

Passing ``run_method`` marks a registration as runnable, which is what ``cmn-run``
offers you and what ``cmn-generate`` writes scripts for:

.. code-block:: python

    Registry.register_configuration(
        config=BenchmarkConfig(),
        name='benchmark',
        namespace='nlp',
        component='mypackage.components.Benchmark',
        run_method='run',
    )

.. toctree::
   :maxdepth: 4
   :hidden:
   :caption: Contents:
   :titlesonly:
