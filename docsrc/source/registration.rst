.. _registration:

Registration
*********************************************

While it is possible to instantiate ``Configuration`` and ``Component`` manually and inline, cinnamon defines a registration-based dependency system.

This system allows to link ``Configuration`` to ``Component`` and ``Configuration`` to other ``Configuration`` by relying on unique identifiers.

These unique identifiers are called ``RegistrationKey``.

=============================================
RegistrationKey
=============================================

A ``RegistrationKey`` is a compound identifier comprising a ``name``, an optional ``tags`` set and a ``namespace``.

.. code-block:: python

    key = RegistrationKey(name='test', tags={'tag1', 'tag2'}, namespace='testing')

``RegistrationKey`` are the fundamental concept of cinnamon as they allow retrieving and building any ``Configuration`` or ``Component`` on the fly.

In particular, by loosely coupling configurations and components via ``RegistrationKey``, we can quickly change them by changing the ``RegistrationKey`` instances.

To understand this fundamental concept, we first need to introduce how coupling is carried out.

=============================================
Registration
=============================================

In cinnamon, **registration** is the action of storing a ``Configuration`` into the ``Registry``, a dynamic lookup table of ``Configuration``.

In other words, the ``Registry`` is a dictionary where each ``RegistrationKey`` corresponds a ``Configuration`` template.

In cinnamon, we have two ways to **register** a ``Configuration``: class methods and ad-hoc functions.

---------------------------------------------
Class method registration
---------------------------------------------

We can directly register a ``Configuration`` template class method via ``register_method()`` function.

.. code-block:: python

    class CustomConfig(cinnamon.configuration.Configuration):

        @classmethod
        @register_method(name='test', tags={'default'}, namespace='testing', component_class=CustomComponent)
        def default(cls):
            config = super(cls).default()

            config.add(name='x', value=5)

            return config

In this example, we **register** the default template of ``CustomConfig`` by specifying the ``RegistrationKey`` attributes and binding ``CustomConfig`` to ``CustomComponent``.

Internally, the ``Registry`` associates the ``RegistrationKey`` defined as (``'test'``, ``{'default'}``, ``'testing'``) to the following information:

- configuration class ``CustomConfig``
- configuration template ``CustomConfig.default()``
- component class ``CustomComponent``

By doing so, cinnamon has all the information to

- instantiate a ``CustomConfig`` instance by calling ``CustomConfig.default()``
- instantiate a ``CustomComponent`` instance by passing ``CustomConfig`` instance attributes.

---------------------------------------------
Ad-hoc registration
---------------------------------------------

There might be cases where we do not need to define custom ``Configuration``, but simply re-use existing ones.

We can still carry out registration via ``register`` decorator and by relying on ``Registry.register_configuration()`` API.

.. code-block:: python

    @register
    def custom_registration():
        Registry.register_configuration(name='test',
                                        tags={'default'},
                                        namespace='testing',
                                        config_class=CustomConfiguration,
                                        component_class=CustomComponent)

Unless specified, the ``default`` configuration template is considered.

Alternatively, we can specify a specific constructor template.

.. code-block:: python

    @register
    def custom_registration():
        Registry.register_configuration(name='test',
                                        tags={'default'},
                                        namespace='testing',
                                        config_class=CustomConfiguration,
                                        config_constructor=CustomConfiguration.custom_constructor,
                                        component_class=CustomComponent)

where ``CustomConfiguration.custom_constructor`` could be defined as follows

.. code-block:: python

        class CustomConfig(cinnamon.configuration.Configuration):

        @classmethod
        def default(cls):
            config = super(cls).default()

            config.add(name='x', value=5)

            return config

        @classmethod
        def custom_constructor(cls):
            config = super(cls).default()

            config.x = 42
            config.add(name='y', value=True)

            return config


=============================================
Retrieving registrations
=============================================

TODO

=============================================
Building instances from registrations
=============================================

TODO

*********************************************
Tl;dr (Too long; didn't read)
*********************************************

- Define your ``Component`` (code logic).
- Define its corresponding ``Configuration`` (one or more).
- Register the ``Configuration`` to the ``Registry`` via a ``RegistrationKey``.
- The ``RegistrationKey`` is a compound string-based unique identifier.
- Build ``Component`` instances via the ``RegistrationKey``.

**Congrats! This is 99% of cinnamon!**

*********************************************
How to use registration APIs
*********************************************

You may be wondering **how** to properly use these registration APIs...

Long story short, you **don't need** to contaminate your code with registration and binding operations.

Cinnamon supports a **specific code organization** to **automatically** address all registration related operations while keeping a clean code organization.

See :doc:`dependencies` for more details.