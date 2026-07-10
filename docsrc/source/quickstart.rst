.. _quickstart:

Quickstart
****************************

Let's consider a data loader class that reads a CSV file from disk.

.. code-block:: python

    import pandas as pd

    class DataLoader:

        def __init__(self, df_path: str):
            self.df_path = df_path

        def load(self):
            return pd.read_csv(self.df_path)

    if __name__ == '__main__':
        loader = DataLoader('path/to/data')
        data = loader.load()

What if we want to run **multiple** ``DataLoader`` instances, each pointing to a
different ``df_path``?

The issue is that ``df_path`` is mixed into the code logic itself.
Changing it means touching the class or its instantiation site — both of which tend
to spread as a project grows.

A cleaner approach is to **separate code logic from configuration**:

.. code-block:: python

    class DataLoaderConfig:

        def __init__(self, df_path: str):
            self.df_path = df_path

    class DataLoader:

        def __init__(self, config: DataLoaderConfig):
            self.config = config

        def load(self):
            return pd.read_csv(self.config.df_path)

    if __name__ == '__main__':
        config = DataLoaderConfig(df_path='path/to/data')
        loader = DataLoader(config)
        data = loader.load()

We now rely on **dependency injection** — the ``DataLoader`` does not know or care
where its parameters come from.

.. note::
    The ``DataLoader``'s API does not change as we swap configurations.

=============================================
Cinnamon
=============================================

Cinnamon formalises this pattern and adds validation, registration, and dependency
resolution on top of it.

Define your configuration by subclassing ``Configuration`` and declaring each field
as a typed class annotation, optionally wrapped with ``Param``:

.. code-block:: python

    from pathlib import Path
    from cinnamon.configuration import Configuration, Param

    class DataLoaderConfig(Configuration):
        df_path: Path = Param(
            'path/to/data',
            description='Path to the CSV file to load'
        )

Define your component by subclassing ``Component``.
The class structure stays exactly as you would write it in plain Python — cinnamon
imposes no additional APIs on your code logic:

.. code-block:: python

    from cinnamon.component import Component

    class DataLoader(Component):

        def __init__(self, df_path: Path):
            self.df_path = df_path

        def load(self):
            return pd.read_csv(self.df_path)

To use both together without the registry:

.. code-block:: python

    if __name__ == '__main__':
        config = DataLoaderConfig.default()
        loader = DataLoader(**config.values)
        data = loader.load()

``config.values`` returns a plain ``{field_name: value}`` dictionary, which unpacks
directly into the component's constructor.

.. note::
    ``DataLoaderConfig.default()`` is equivalent to ``DataLoaderConfig()``.
    It returns a ``DataLoaderConfig`` instance with all fields set to their defaults.

=============================================
Registration
=============================================

In practice, cinnamon encourages a **register, bind, and build** workflow rather
than directly instantiating configurations and components.

Once you have defined a ``Configuration`` and its corresponding ``Component``,
you **register** the configuration in the ``Registry`` and **bind** it to the component.
This is done via a ``RegistrationKey``: a compound identifier made up of a ``name``,
an optional ``tags`` set, and a ``namespace``.

The most concise way to register is the ``@register_method`` decorator on a
``@classmethod`` of your ``Configuration``:

.. code-block:: python

    from cinnamon.configuration import Configuration, Param
    from cinnamon.registry import register_method

    class DataLoaderConfig(Configuration):
        df_path: Path = Param(
            'path/to/data',
            description='Path to the CSV file to load'
        )

        @classmethod
        @register_method(
            name='data_loader',
            tags={'test'},
            namespace='showcasing',
            component='components.DataLoader'   # module path as a string
        )
        def default(cls) -> 'DataLoaderConfig':
            return super().default()

Alternatively, you can register programmatically using ``Registry.register_configuration()``
inside a function decorated with ``@register``:

.. code-block:: python

    from cinnamon.registry import Registry, register

    @register
    def register_data_loader():
        Registry.register_configuration(
            config=DataLoaderConfig.default(),
            name='data_loader',
            tags={'test'},
            namespace='showcasing',
            component='components.DataLoader'
        )

Both approaches are equivalent. The ``@register_method`` style is more concise when
the registration lives naturally on the configuration class. The ``@register`` style
is useful when you want to re-use an existing ``Configuration`` without subclassing it.

=============================================
Building
=============================================

The ``Registry`` does not execute registrations eagerly.
Instead, call ``Registry.build()`` to scan your project's ``configurations`` folder,
run all ``@register`` and ``@register_method`` decorators it finds, and resolve the
full dependency graph:

.. code-block:: python

    from pathlib import Path
    from cinnamon.registry import Registry

    Registry.build(directory=Path('.'))

After a successful build, construct a ``DataLoader`` instance from its registered key:

.. code-block:: python

    # Via the Registry directly
    loader = Registry.instantiate_component(
        name='data_loader',
        tags={'test'},
        namespace='showcasing'
    )

    # Or via the Component class (syntactic sugar — also type-checks the result)
    loader = DataLoader.instantiate(
        name='data_loader',
        tags={'test'},
        namespace='showcasing'
    )

    data = loader.load()

The ``Registry`` builds the ``DataLoaderConfig`` instance, resolves any dependencies,
validates all conditions, and passes ``config.values`` to ``DataLoader.__init__``
automatically.

To swap the underlying implementation, you only need to change the ``RegistrationKey``
— the calling code stays the same.

=============================================
Beyond quickstart
=============================================

The **register, bind, and build** workflow unlocks a number of powerful features:

- **Nesting** ``Component`` and ``Configuration`` to compose more sophisticated pipelines.
- Automatically generating ``Configuration`` **variants** for hyperparameter search.
- Integrating **external** ``Component`` and ``Configuration`` written by other users.
- Static and dynamic **condition** validation.

See `Configuration <https://nlp-unibo.github.io/cinnamon/configuration.html>`_ for a
full walkthrough of parameters, conditions, variants, and nesting.

See `Registration <https://nlp-unibo.github.io/cinnamon/registration.html>`_ for more
details on how to structure registration code and use the ``Registry`` APIs.

.. toctree::
   :maxdepth: 4
   :hidden:
   :caption: Contents:
   :titlesonly: