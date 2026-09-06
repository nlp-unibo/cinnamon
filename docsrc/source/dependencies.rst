.. _dependencies:

Registration Dependencies
*********************************************

In :doc:`registration`, we saw that
cinnamon pairs a ``Configuration`` to its component via a ``RegistrationKey``.
Moreover, ``Configuration`` instances can nest other ``Configuration`` instances to compose
more sophisticated ones (see :doc:`configuration`).

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

    class DataLoader:

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
Depending on many registrations
=============================================

A dependency field can hold a ``list`` of keys, or a ``dict`` of them keyed by
string. Use a list when order is what matters — a pipeline of stages, a set of loss
terms — and a dict when the members need names:

.. code-block:: python

    from cinnamon.configuration import Configuration, Param
    from cinnamon.registry import RegistrationKey, Registry

    def key(name):
        return RegistrationKey(name=name, namespace='nlp')

    class ModelConfig(Configuration):
        losses: list[RegistrationKey] = Param([key('cross_entropy'), key('sparsity')])
        metrics: dict[str, RegistrationKey] = Param({'accuracy': key('accuracy')})

Every member becomes an edge in the dependency graph, so a typo in any one of them
is reported by ``cmn-check`` rather than surfacing when you try to build.

The component receives the container of keys, exactly as declared.
:meth:`~cinnamon.registry.Registry.from_keys` builds the whole thing while keeping
its shape:

.. code-block:: python

    class Model:

        def __init__(self, losses, metrics):
            self.losses = Registry.from_keys(losses)     # list -> list, in order
            self.metrics = Registry.from_keys(metrics)   # dict -> dict, same labels

It accepts a single key too, so a field typed
``RegistrationKey | list[RegistrationKey]`` needs no branch, and passes ``None``
through so an optional dependency left unset stays unset. It builds eagerly — keep
an explicit loop when a child should only be built under some condition.

Only one level of nesting is supported. ``list[list[RegistrationKey]]`` and
``dict[str, list[RegistrationKey]]`` raise ``TypeError`` when the dependency is
inspected, with a message saying so.

---------------------------------------------
Varying a container
---------------------------------------------

A container varies **as a whole container**. Each variant is a complete
replacement for the field's value, and lists and dicts behave the same way:

.. code-block:: python

    class ModelConfig(Configuration):
        losses: list[RegistrationKey] = Param(
            [CE],
            variants=[[CE, SPARSITY], []],          # add one, or drop them all
        )
        metrics: dict[str, RegistrationKey] = Param(
            {'acc': ACCURACY},
            variants=[{'acc': ACCURACY, 'f1': F1}],  # labels vary too
        )

Everything that applies to an ordinary variant applies here. A container variant
combines with the other varying fields, so the sweep is still the full product; a
member that appears only inside a variant is a dependency like any other, checked
and resolved; and a variant identical to the default is rejected, because it
changes nothing.

.. note::
    **A container does not multiply its members' variants into the parent, while a
    scalar dependency does.** Three losses with three variants each would otherwise
    be twenty-seven parent keys from a single field. Those member variants are
    still registered and usable on their own -- they simply do not compose upward.
    To vary a container, vary the whole thing.

.. note::
    Container variants are tagged by index -- ``losses=variant-1`` -- because the
    contents of a list or dict do not reduce to a short, stable label the way a
    scalar value does. The index follows declaration order, so keys stay the same
    across runs and machines, but the tag does not tell you what is in the
    variant. ``cmn-check`` prints an **Indexed Variants** section saying what each
    one holds.

=============================================
External dependencies
=============================================

Cinnamon is designed to be a community framework. You may need to import
configurations and components written by others and build on top of them.

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