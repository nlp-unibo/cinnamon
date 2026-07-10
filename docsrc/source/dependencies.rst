.. _dependencies:

Registration Dependencies
*********************************************

In `registration <https://nlp-unibo.github.io/cinnamon/registration.html>`_, we saw that
cinnamon pairs ``Configuration`` to ``Component`` via ``RegistrationKey``.
Moreover, ``Configuration`` instances can nest other ``Configuration`` instances to compose
more sophisticated ones (see `configuration <https://nlp-unibo.github.io/cinnamon/configuration.html>`_).

What remains is the question of **how** to organise code so that cinnamon can find and
wire everything together automatically.

=============================================
Code organisation
=============================================

Registration functions (either ``@classmethod`` decorators or ad-hoc ``@register`` functions)
can technically be written anywhere.
However, cinnamon's ``Registry`` only scans files inside a folder named ``configurations``.
This constraint is intentional: it avoids accidentally executing unrelated code during
the registration scan.

The recommended project layout is:

.. code-block::

    project_folder/
        configurations/
            data_loader.py
        components/
            data_loader.py

A ``components`` folder is not required, but pairing component and configuration files
by name makes it easy to navigate the project.

For the above example the files would look like:

``components/data_loader.py``

.. code-block:: python

    from cinnamon.component import Component

    class DataLoader(Component):

        def __init__(self, folder_name: str):
            self.folder_name = folder_name

        def load(self):
            ...

``configurations/data_loader.py``

.. code-block:: python

    from pathlib import Path
    from cinnamon.configuration import Configuration, Param
    from cinnamon.registry import Registry, RegistrationKey, register_method

    class DataLoaderConfig(Configuration):
        folder_name: str = Param('my_custom_folder', description='folder to load data from')

        @classmethod
        @register_method(name='loader', tags={'default'}, namespace='testing',
                         component='components.DataLoader')
        def default(cls) -> 'DataLoaderConfig':
            return super().default()

.. note::
    Defining a ``components`` folder is not mandatory, but it improves readability
    by allowing users to quickly pair components and configurations.


=============================================
Resolving dependencies
=============================================

Registering and nesting ``Configuration`` can quickly lead to dependency ordering problems.
The addition of ``Configuration`` variants can further complicate this.

To avoid requiring users to manually order registrations, cinnamon builds a
dependency graph automatically — **independently of the registration order**.

Consider the following two nested configurations:

.. code-block:: python

    from cinnamon.configuration import Configuration, Param
    from cinnamon.registry import RegistrationKey

    class NestedChild(Configuration):
        x: int = Param(42)

    class ParentConfig(Configuration):
        param_1: bool = Param(True)
        param_2: bool = Param(False)
        child: RegistrationKey = Param(
            RegistrationKey(name='test', tags={'nested'}, namespace='testing')
        )

The two registration functions below produce identical dependency graphs,
regardless of the order in which they register the parent and child:

.. code-block:: python

    from cinnamon.registry import Registry, register

    @register
    def custom_registration():
        Registry.register_configuration(
            config=ParentConfig.default(),
            name='test', tags={'parent'}, namespace='testing'
        )
        Registry.register_configuration(
            config=NestedChild.default(),
            name='test', tags={'nested'}, namespace='testing'
        )

    @register
    def custom_registration():
        # Order reversed — the result is identical
        Registry.register_configuration(
            config=NestedChild.default(),
            name='test', tags={'nested'}, namespace='testing'
        )
        Registry.register_configuration(
            config=ParentConfig.default(),
            name='test', tags={'parent'}, namespace='testing'
        )

.. note::
    The same ordering independence applies to ``@register_method`` decorators.

This is possible because the ``Registry`` builds a directed acyclic graph (DAG) of
dependencies and resolves them bottom-up — children before parents — regardless of
the order they were registered.

To trigger registration and resolution, call ``Registry.build()``:

.. code-block:: python

    from pathlib import Path
    from cinnamon.registry import Registry

    Registry.build(directory=Path('.'))

This instructs the ``Registry`` to scan all ``configurations`` folders under the
current working directory, execute every ``@register`` and ``@register_method``
decorator it finds, and then resolve the full dependency graph.

.. note::
    ``Registry.build()`` searches recursively — nested ``configurations`` folders
    within subdirectories are also picked up automatically.


=============================================
External dependencies
=============================================

Cinnamon is designed to be a community framework. You may need to import
``Configuration`` and ``Component`` definitions written by others and build on top of them.

The ``Registry`` supports loading registrations from directories outside your own project.
You can also define ``Configuration`` fields that point to externally registered keys.

For example, suppose a ``DataLoaderConfig`` variant depends on an external preprocessor:

.. code-block:: python

    from cinnamon.configuration import Configuration, Param
    from cinnamon.registry import RegistrationKey, register_method

    class DataLoaderConfig(Configuration):
        folder_name: str = Param('my_custom_folder')

        @classmethod
        @register_method(name='loader', tags={'default'}, namespace='testing',
                         component='components.DataLoader')
        def default(cls) -> 'DataLoaderConfig':
            return super().default()

        @classmethod
        @register_method(name='loader', tags={'external'}, namespace='testing',
                         component='components.DataLoader')
        def external_variant(cls) -> 'DataLoaderConfig':
            config = cls()
            # processor is defined in an external project
            config = config.model_copy(update={
                'processor': RegistrationKey(name='processor', namespace='external')
            })
            return config

.. note::
    To use ``model_copy`` to add a new field, the field must already be declared
    on the class. If ``processor`` is not declared in ``DataLoaderConfig``, add it
    as an optional field:

    .. code-block:: python

        from typing import Optional

        class DataLoaderConfig(Configuration):
            folder_name: str = Param('my_custom_folder')
            processor: Optional[RegistrationKey] = Param(None)

To avoid a ``NamespaceNotFoundException`` when the external key is resolved, inform
the ``Registry`` where that namespace was declared by passing ``external_directories``
to ``Registry.build()``:

.. code-block:: python

    Registry.build(
        directory=Path('.'),
        external_directories=[Path('path/to/external/project')]
    )

The ``Registry`` will scan the external project's ``configurations`` folder,
register its keys, and make them available for dependency resolution alongside
your own.


.. toctree::
   :maxdepth: 4
   :hidden:
   :caption: Contents:
   :titlesonly: