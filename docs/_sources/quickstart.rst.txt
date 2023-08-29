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

****************************
Cinnamon
****************************

In ``cinnamon`` we follow the above paradigm.

.. code-block:: python

    class DataLoaderConfig(cinnamon_core.core.configuration.Configuration):

        @classmethod
        def get_default(cls):
            config = super().get_default()

            config.add(name='df_path',
                       value='path/to/data',
                       type_hint=Path,
                       description='path where to load data')

            return config


    class DataLoader(cinnamon_core.core.component.Component):

        def load():
            df = pd.read_csv(self.config.df_path)
            return df

    if __name__ = '__main__':
        config = DataLoaderConfig.get_default()
        loader = DataLoader(config)
        data = loader.load()

Configurations are ``cinnamon_core.core.configuration.Configuration`` subclasses, where the ``get_default()`` method
defines the standard template of the configuration.

You can **add parameters** to the configuration via ``add()`` method.
Each parameter is defined by a ``name``, a ``value``, and, optionally, info about its type, textual description, variants, allowed value range and more...
All this information allows ``cinnamon`` checking whether the defined ``Configuration`` is **valid** or not.

The code logic is a ``cinnamon_core.core.component.Component`` subclass and maintains the same code structure **with minimal modifications**.
In particular, components can be defined as you would normally define a standard python class.


-------------------------
Registration
-------------------------

In ``cinnamon``, we **don't explicitly** instantiate a ``Configuration`` and its corresponding ``Component`` as done in previous sections.

Instead, ``cinnamon`` supports a **registration, bind, and build** paradigm.

Once, we have defined the ``Configuration`` and its corresponding ``Component``, we **register** the ``Configuration``.

.. code-block:: python

    Registry.add_configuration(config_class=DataLoaderConfig,
                               name='data_loader',
                               tags={'test'},
                               namespace='showcasing')

We do so by using a ``RegistrationKey`` defined as a (``name``, ``tags``, ``namespace``) tuple.

Then we ``bind`` the ``Configuration`` to the ``Component`` using the ``RegistrationKey``.

.. code-block:: python

    Registry.bind(component_class=DataLoader,
                  name='data_loader',
                  tags={'test'},
                  namespace='showcasing')

Now, ``cinnamon`` knows that we want to create ``DataLoader`` instances via ``DataLoaderConfig``.

We just need to build our first instance.

.. code-block:: python

    loader = Registry.build_component(name='data_loader',
                                      tags={'test'},
                                      namespace='showcasing')

or

.. code-block:: python

    loader = DataLoader.build_component(name='data_loader',
                                        tags={'test'},
                                        namespace='showcasing')

to return a ``DataLoader`` instance rather than a generic ``Component``.

Now, we can build ``DataLoader`` instances anywhere in our code by simply using the associated ``RegistrationKey``.


****************************
Beyond quickstart
****************************

``cinnamon`` uses the **registration, bind, and build** to provide flexible, clean and easy to extend code.
The main code dependency are ``RegistrationKey`` instances.

Via this paradigm, ``cinnamon`` supports:

- `**Nesting** <https://federicoruggeri.github.io/cinnamon_core/configuration.html#nested-configurations>`_ ``Component`` and ``Configuration`` to build more sophisticated ones.
- Automatically generating ``Configuration`` `**variants** <https://federicoruggeri.github.io/cinnamon_core/configuration.html#configuration-variants>`_.
- Quick integration of `**external** <https://federicoruggeri.github.io/cinnamon_core/dependencies.html#external-registrations>`_ ``Component`` and ``Configuration`` (e.g., written by other users).
- Static and dynamic code `**sanity check** <https://federicoruggeri.github.io/cinnamon_core/configuration.html>`_.

