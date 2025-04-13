.. _quickstart:

Quickstart
****************************

Let's consider a data loader class that loads and returns some data.

.. code-block:: python

    class DataLoader:

        def __init__(df_path):
            self.df_path = df_path

        def load():
            df = pd.read_csv(self.df_path)
            return df

    if __name__ == '__main__':
        loader = DataLoader('path/to/data')
        data = loader.load()

What if we want to define **multiple** ``DataLoader``, each pointing to a different ``df_path``?

We notice that we are **mixing** code logic (i.e., the ``DataLoader`` class) with its configuration (i.e., ``df_path``).

We can **separate** code logic from configuration.

Instead of relying on additional data formats (e.g., JSON), we define a ``DataLoaderConfig`` in python.

.. code-block:: python

    class DataLoaderConfig:

        def __init__(df_path):
            self.df_path = df_path

    class DataLoader:

        def __init__(config: DataLoaderConfig):
            self.config = config

        def load():
            df = pd.read_csv(self.config.df_path)
            return df

    if __name__ = '__main__':
        config = DataLoaderConfig(df_path='path/to/data')
        loader = DataLoader(config)
        data = loader.load()

Now, we are relying on **dependency injection** to separate code logic and configuration.

.. note::
    The ``DataLoader``'s APIs do not change as we change the configuration.

=============================================
Cinnamon
=============================================

In ``cinnamon`` we follow the above paradigm.

.. code-block:: python

    from cinnamon.configuration import Configuration
    from cinnamon.component import Component

    class DataLoaderConfig(Configuration):

        @classmethod
        def default(cls):
            config = super().default()

            config.add(name='df_path',
                       value='path/to/data',
                       type_hint=Path,
                       description='path where to load data')

            return config


    class DataLoader(Component):

        def __init__(self, df_path):
            self.df_path = df_path

        def load():
            df = pd.read_csv(self.df_path)
            return df

    if __name__ = '__main__':
        config = DataLoaderConfig.default()
        loader = DataLoader(**config.values)
        data = loader.load()

Configurations are ``cinnamon.configuration.Configuration`` subclasses, where the ``default()`` method
defines the standard template of the configuration.

You can **add parameters** to the configuration via ``add()`` method.

Each parameter is defined by a ``name``, a ``value``, and, optionally, info about its type, textual description, variants, allowed value range and more...

All this information allows ``cinnamon`` checking whether the defined ``Configuration`` is **valid** or not.

The code logic is a ``cinnamon.component.Component`` subclass and maintains the same code structure **with no modifications**.

In particular, components can be defined as you would normally define a standard python class.

=============================================
Registration
=============================================

In ``cinnamon``, we usually **don't explicitly** instantiate a ``Configuration`` and its corresponding ``Component`` as done in the previous section.

Instead, ``cinnamon`` supports a **registration, bind, and build** paradigm.

Once, we have defined the ``Configuration`` and its corresponding ``Component``, we **register** the ``Configuration``.

.. code-block:: python

    Registry.register_configuration(config_class=DataLoaderConfig,
                               name='data_loader',
                               tags={'test'},
                               namespace='showcasing',
                               component_class=DataLoader)

or

.. code-block:: python

    class DataLoaderConfig(Configuration):

        @classmethod
        @register_method(name='data_loader',
                         tags={'test'},
                         namespace='showcasing',
                         component_class=DataLoader)
        def default(cls):
            config = super().default()

            config.add(name='df_path',
                       value='path/to/data',
                       type_hint=Path,
                       description='path where to load data')

            return config

We do so by using a ``RegistrationKey`` defined as a (``name``, ``tags``, ``namespace``) tuple.

Additionally, we **bind** the ``Configuration`` to a ``Component`` so that ``cinnamon`` knows that we want to create ``DataLoader`` instances via ``DataLoaderConfig``.

At this point, we only need to build our first instance via the ``RegistrationKey``.

.. code-block:: python

    loader = DataLoader.build_component(name='data_loader',
                                        tags={'test'},
                                        namespace='showcasing')

to return a ``DataLoader``.

Now, we can build ``DataLoader`` instances anywhere in our code by simply using the associated ``RegistrationKey``.

.. note::
    If you want to quickly change the ``Configuration`` of your ``DataLoader``, **you only need to change the key!**


=============================================
Beyond quickstart
=============================================

``cinnamon`` uses the **registration, bind, and build** to provide flexible, clean and easy to extend code.

The main code dependency are ``RegistrationKey`` instances.
See `Registration <https://nlp-unibo.github.io/cinnamon/registration.html/>`_ if you want to know more about how to set up your code with ``cinnamon``.

Via this paradigm, ``cinnamon`` supports:

- **Nesting** ``Component`` and ``Configuration`` to build more sophisticated ones.
- Automatically generating ``Configuration`` **variants**.
- Quick integration of **external** ``Component`` and ``Configuration`` (e.g., written by other users).
- Static and dynamic code **sanity check**.

See `Configuration <https://nlp-unibo.github.io/cinnamon/configuration.html/>`_ for more details.