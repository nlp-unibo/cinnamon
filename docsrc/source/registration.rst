.. _registration:

Registration
*********************************************

While configurations and components can be instantiated manually, cinnamon provides a
**registration-based dependency system** that links them together via unique identifiers
called ``RegistrationKey``.

This system allows the ``Registry`` to build ``Configuration`` and ``Component``
instances on demand, resolve nested dependencies automatically, and enumerate valid
parameter variants — all without the caller knowing which concrete classes are involved.

=============================================
RegistrationKey
=============================================

A ``RegistrationKey`` is a compound identifier made up of three fields:

- ``name``: a general identifier for the registered ``Configuration``.
- ``namespace``: a high-level grouping, useful for distinguishing between user groups,
  frameworks, or macro categories. Follows the convention ``user/namespace``
  (e.g. ``"huggingface/transformers"``), though any string is valid. Defaults to
  ``"default"`` if not provided.
- ``tags``: an optional ``set`` of strings that disambiguates keys sharing the same
  ``name`` and ``namespace`` (e.g. multiple model variants by the same author).

.. code-block:: python

    from cinnamon.registry import RegistrationKey

    key = RegistrationKey(name='model', tags={'bert', 'large'}, namespace='nlp')

Two keys are equal if and only if their ``name``, ``tags``, and ``namespace`` all match:

.. code-block:: python

    key_a = RegistrationKey(name='model', tags={'bert'}, namespace='nlp')
    key_b = RegistrationKey(name='model', tags={'bert'}, namespace='nlp')
    key_c = RegistrationKey(name='model', tags={'gpt'},  namespace='nlp')

    key_a == key_b  # True
    key_a == key_c  # False

``RegistrationKey`` has a canonical string representation and can be round-tripped
through it:

.. code-block:: python

    key = RegistrationKey(name='model', tags={'bert'}, namespace='nlp')
    str(key)
    # 'name=model--tags=['bert']--namespace=nlp'

    restored = RegistrationKey.from_string(str(key))
    restored == key     # True

    # parse() accepts a key object, its string form, or name/tags/namespace directly
    RegistrationKey.parse(name='model', tags={'bert'}, namespace='nlp') == key  # True

=============================================
Registration
=============================================

**Registration** is the action of storing a ``Configuration`` instance in the ``Registry``,
optionally binding it to a ``Component`` class so that component instances can be built
from it later.

There are two ways to register: via a decorated ``@classmethod``, or via an ad-hoc
function.

---------------------------------------------
Class method registration
---------------------------------------------

Decorate a ``@classmethod`` of your ``Configuration`` with ``@register_method`` to
register it automatically when the ``Registry`` scans your ``configurations`` folder:

.. code-block:: python

    from cinnamon.configuration import Configuration, Param
    from cinnamon.registry import register_method

    class CustomConfig(Configuration):
        x: int = Param(5, description='An example parameter')

        @classmethod
        @register_method(
            name='test',
            tags={'default'},
            namespace='testing',
            component='components.CustomComponent'
        )
        def default(cls) -> 'CustomConfig':
            return super().default()

When the ``Registry`` processes this file, it:

1. Stores a ``ConfigurationInfo`` entry keyed by ``RegistrationKey(name='test', tags={'default'}, namespace='testing')``.
2. Records that ``CustomConfig.default()`` is the constructor to call.
3. Binds the result to ``components.CustomComponent`` (the component's module path as a string).

Any ``@classmethod`` can be decorated, not just ``default()``. This is useful for
registering multiple templates from the same ``Configuration`` class:

.. code-block:: python

    class CustomConfig(Configuration):
        x: int = Param(5)
        y: float = Param(0.01)

        @classmethod
        @register_method(name='test', tags={'small'}, namespace='testing',
                         component='components.CustomComponent')
        def default(cls) -> 'CustomConfig':
            return super().default()

        @classmethod
        @register_method(name='test', tags={'large'}, namespace='testing',
                         component='components.CustomComponent')
        def large(cls) -> 'CustomConfig':
            return cls(x=100, y=0.001)

---------------------------------------------
Ad-hoc registration
---------------------------------------------

When you want to register an existing ``Configuration`` without subclassing it,
use the ``@register`` decorator and call ``Registry.register_configuration()`` directly:

.. code-block:: python

    from cinnamon.registry import Registry, register

    @register
    def custom_registration():
        Registry.register_configuration(
            config=CustomConfig.default(),
            name='test',
            tags={'default'},
            namespace='testing',
            component='components.CustomComponent'
        )

This is equivalent to ``@register_method`` but keeps the registration logic separate
from the ``Configuration`` class — useful when re-using an existing configuration
without modification.

---------------------------------------------
Runnable components
---------------------------------------------

If a ``Component`` exposes a method that should be invoked automatically when run via
``cmn-run``, specify it with the ``run_method`` argument:

.. code-block:: python

    Registry.register_configuration(
        config=CustomConfig.default(),
        name='test',
        tags={'runnable'},
        namespace='testing',
        component='components.CustomComponent',
        run_method='train'          # calls component.train() when run via cmn-run
    )

    # or via @register_method:
    @register_method(name='test', tags={'runnable'}, namespace='testing',
                     component='components.CustomComponent', run_method='train')
    def default(cls) -> 'CustomConfig':
        return super().default()

Registered runnable keys carry the internal ``__runnable`` special tag and can be
retrieved with ``Registry.retrieve_runnable_keys()``.

=============================================
Retrieving registrations
=============================================

After ``Registry.build()`` (or ``Registry.dag_resolution()`` in manual workflows),
you can query the registry by key or by field filters.

**Retrieve a configuration instance** by its key:

.. code-block:: python

    config = Registry.retrieve_configuration(
        name='test', tags={'default'}, namespace='testing'
    )

**Retrieve full registration info** (configuration + bound component + run method):

.. code-block:: python

    info = Registry.retrieve_configuration_info(
        name='test', tags={'default'}, namespace='testing'
    )
    info.config         # the Configuration instance
    info.component      # 'components.CustomComponent' (string) or None
    info.run_method     # 'train' or None

Both methods also accept a ``RegistrationKey`` instance directly:

.. code-block:: python

    key = RegistrationKey(name='test', tags={'default'}, namespace='testing')
    config = Registry.retrieve_configuration(registration_key=key)

**Search for keys** using ``retrieve_keys()``, which supports filtering by name,
namespace, tags, or any combination:

.. code-block:: python

    # All keys in a namespace
    keys = Registry.retrieve_keys(namespaces='testing')

    # All keys matching a name and namespace
    keys = Registry.retrieve_keys(names='test', namespaces='testing')

    # All keys with specific tags
    keys = Registry.retrieve_keys(tags={'default'})

    # All runnable keys
    keys = Registry.retrieve_runnable_keys()

``Configuration`` also provides a ``retrieve()`` classmethod as syntactic sugar that
additionally type-checks the result:

.. code-block:: python

    config = CustomConfig.retrieve(name='test', tags={'default'}, namespace='testing')
    # raises RuntimeError if the retrieved config is not a CustomConfig instance

=============================================
Building instances from registrations
=============================================

Build a ``Configuration`` instance via its key:

.. code-block:: python

    config = Registry.retrieve_configuration(
        name='test', tags={'default'}, namespace='testing'
    )
    config.x    # >>> 5

Build the bound ``Component`` instance:

.. code-block:: python

    # Via the Registry
    component = Registry.instantiate_component(
        name='test', tags={'default'}, namespace='testing'
    )

    # Via the Component class (type-checks the result)
    component = CustomComponent.instantiate(
        name='test', tags={'default'}, namespace='testing'
    )
    component.x     # >>> 5

See `component <https://nlp-unibo.github.io/cinnamon/component.html>`_ for the full
details of how component construction works, including nested configurations and
``build_args`` overrides.

=============================================
Deferred dependency resolution
=============================================

By default, the ``Registry`` resolves all ``RegistrationKey`` dependencies in a
configuration — replacing them with the corresponding ``Configuration`` instances.

If you need to keep dependencies as ``RegistrationKey`` objects after resolution
(for example, to build the component lazily at runtime), pass
``resolve_automatically=False`` at registration time:

.. code-block:: python

    Registry.register_configuration(
        config=MyConfig.default(),
        name='model',
        namespace='testing',
        resolve_automatically=False
    )

    # After Registry.dag_resolution():
    config = MyConfig.retrieve(name='model', namespace='testing')
    isinstance(config.child, RegistrationKey)   # True — not resolved to a Configuration

The ``Registry`` still validates the key's existence and checks conditions, but the
dependency field is left as a ``RegistrationKey`` for the caller to resolve manually.

=============================================
Tl;dr
=============================================

- Define your ``Component`` (code logic).
- Define its corresponding ``Configuration`` (one or more).
- Register the ``Configuration`` in the ``Registry`` via a ``RegistrationKey``.
- A ``RegistrationKey`` is a ``(name, tags, namespace)`` compound identifier.
- Build ``Configuration`` instances via the ``RegistrationKey``.
- Build ``Component`` instances via the ``RegistrationKey``.

**Congrats! This is 99% of cinnamon.**

=============================================
How to use registration APIs
=============================================

You do not need to scatter registration calls throughout your codebase.
Cinnamon supports a **specific code organisation** that handles all registration
automatically while keeping things readable.

See `dependencies <https://nlp-unibo.github.io/cinnamon/dependencies.html>`_ for the
recommended project layout and a full walkthrough of how ``Registry.build()`` discovers
and executes registrations.


.. toctree::
   :maxdepth: 4
   :hidden:
   :caption: Contents:
   :titlesonly: