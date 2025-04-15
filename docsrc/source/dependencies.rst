.. _dependencies:

Registration Dependencies
*********************************************

In `registration <https://nlp-unibo.github.io/cinnamon/registration.html>`_, we have seen that cinnamon pairs ``Configuration`` to ``Component`` via ``RegistrationKey``.
Moreover, ``Configuration`` can be nested to indirectly define nested ``Component`` (see `configuration <https://nlp-unibo.github.io/cinnamon/configuration.html>`_).

We are only left to the question of **how** should we use these APIs to work with cinnamon.

=============================================
Code Organization
=============================================

Ideally, registration functions (either class methods or ad-hoc functions) can be written anywhere: it is up to the ``Registry`` to find these functions and run them to populate itself with ``RegistrationKey`` and associated configuration and component information.

Nonetheless, cinnamon is designed to check only registration functions written in files located in ``configurations`` folder.
This choice is meant to avoid unwanted code executions when checking python files.

Therefore, we recommend organizing your code as follows

.. code-block::

    project_folder
        configurations
            folder containing ``Configuration`` scripts

        components
            folder containing ``Component`` scripts

We also recommend using the same filename for <``Configuration``, ``Component``> paired scripts for readability purposes.

For instance, if we define a data loader component, our code organization will be

.. code-block::

    project_folder
        configurations
            data_loader.py

        components
            data_loader.py

where

components/data_loader.py
    .. code-block:: python

        class DataLoader(Component):

            def load(...):
                ...

configurations/data_loader.py
    .. code-block:: python

        class DataLoaderConfig(Configuration):

            @classmethod
            @register_method(name='loader', tags={'default'}, namespace='testing', component_class=DataLoader)
            def default(cls):
                config = super(cls).default()

                config.add(name='folder_name', type_hint=str, value='my_custom_folder')

                return config

.. note::
    Defining a ``components`` folder is not mandatory, but it improves readability by allowing users to quickly pair components and configurations.


=============================================
Resolving dependencies
=============================================

Registering and nesting ``Configuration`` can quickly lead to a dependency problem.
Furthermore, the addition of ``Configuration`` variants may further exacerbate the issue.

To avoid users manually ordering registrations to avoid conflicts, cinnamon dynamically builds a dependency graphs, **independently** of the registration order.

For instance, consider the following nesting dependency between two configurations:

.. code-block:: python

    class ParentConfig(cinnamon.configuration.Configuration):

        @classmethod
        def default(
                cls
        ):
            config = super(cls).default()

            config.add(name='param_1', value=True)
            config.add(name='param_2', value=False)
            config.add(name='child',
                       value=RegistrationKey(name='test', tags={'nested'}, namespace='testing'))
            return config


    class NestedChild(Configuration):

        @classmethod
        def default(
                cls
        ):
            config = super().default()

            config.add(name='x', value=42)

            return config

The following registration functions produce the same dependency graph.

.. code-block:: python

    @register
    def custom_registration():
        Registry.register_configuration(config_class=ParentConfig,
                                        name='test',
                                        tags={'parent'},
                                        namespace='testing',
                                        )
        Registry.register_configuration(config_class=NestedChild,
                                        name='test',
                                        tags={'nested'},
                                        namespace='testing',
                                        )

    @register
    def custom_registration():
        Registry.register_configuration(config_class=NestedChild,
                                        name='test',
                                        tags={'nested'},
                                        namespace='testing',
                                        )
        Registry.register_configuration(config_class=ParentConfig,
                                        name='test',
                                        tags={'parent'},
                                        namespace='testing',
                                        )

.. note::
    The same reasoning applies for class method registrations (i.e., via ``register_method`` decorator).

This code organization is meant to simplify registration burden while keeping high readability.

Behind the curtains, the ``Registry`` is issued to look for all ``@register`` and ``@register_method`` decorators located in ``configurations`` folder
to automatically execute them.

This action is handled by ``Registry.setup()`` method.

.. code-block:: python

    Registry.setup(directory=Path('.'))

Issues the ``Registry`` to look for all ``configurations`` folder(s) under the current working directory.

.. note::
    The ``Registry`` search for registrations also accounts for nested ``configurations`` folders in a given directory.

=============================================
External dependencies
=============================================

Cinnamon is a community project. This means that **you** are the main contributor.

In many situations, you may need to import other's work: external configurations and components.

Cinnamon supports loading registration function calls that are external to your project's ``configurations`` folder.
Moreover, you can also build your ``Configuration`` and ``Component`` with dependencies on external ones.

For instance, suppose that a ``DataLoaderConfig`` variant has a external dependency.

.. code-block:: python

    class DataLoaderConfig(Configuration):

        @classmethod
        def default(cls):
            config = super(cls).get_default()

            config.add(name='folder_name', type_hint=str)

            return config

        @classmethod
        @register_method(name='loader', tags={'external'}, namespace='testing')
        def external_variant(cls):
            config = cls.default()

            config.add(name='processor', value=RegistrationKey(name='processor', namespace='external'))

            return config

In this case, to avoid incurring in errors, we need to inform the ``Registry`` where ``RegistrationKey(name='processor', namespace='external')`` has been declared.

We do so, by specifying the main external directory when issuing ``Registry.setup()``.

.. code-block:: python

    Registry.setup(directory=Path('.'), external_directories=[Path('path/to/external/directory')])


.. toctree::
   :maxdepth: 4
   :hidden:
   :caption: Contents:
   :titlesonly:

