.. _configuration:

Configuration
*********************************************

A ``Configuration`` is a `Pydantic <https://docs.pydantic.dev/latest/>`_ ``BaseModel`` subclass
that stores all the parameters of a ``Component``.
Each field is defined as a typed class annotation, optionally wrapped with ``Param`` to attach
cinnamon-specific metadata such as descriptions, tags, and variants.

=============================================
Param
=============================================

``Param`` is a wrapper around Pydantic's ``Field`` that accepts all standard ``Field`` arguments
and additionally supports three cinnamon-specific keyword arguments:

- ``tags``: a ``set`` of arbitrary string keywords for grouping and searching parameters.
- ``variants``: a ``list`` of alternative values for automated configuration search.
- ``description``: a human-readable description of the parameter.

.. code-block:: python

    from cinnamon.configuration import Configuration, Param

    class MyConfig(Configuration):
        x: int = Param(5, description='An example integer parameter', tags={'number'})

The first positional argument is the default value.
Passing ``...`` (Ellipsis) marks the field as required — no default will be used and
Pydantic will raise a ``ValidationError`` if the field is omitted at instantiation.

.. code-block:: python

    class MyConfig(Configuration):
        x: int = Param(...)     # required: must be provided at instantiation
        y: int = Param(5)       # optional: defaults to 5

Plain Python defaults are also accepted without ``Param``.
In that case, cinnamon automatically injects empty ``tags`` and ``variants`` metadata:

.. code-block:: python

    class MyConfig(Configuration):
        x: int = 5              # equivalent to Param(5, tags=set(), variants=[])


---------------------------------------------
Accessing parameter metadata
---------------------------------------------

Each ``Configuration`` exposes a ``meta`` descriptor that provides access to field metadata
(``tags`` and ``variants``) at both class level and instance level.

.. code-block:: python

    class MyConfig(Configuration):
        x: int = Param(5, tags={'number'}, variants=[10, 20])

    # Class-level access (reads from model_fields)
    MyConfig.meta.x.tags        # >>> {'number'}
    MyConfig.meta.x.variants    # >>> [10, 20]

    # Instance-level access (reads from a per-instance copy of metadata)
    config = MyConfig()
    config.meta.x.tags          # >>> {'number'}
    config.meta.x.variants      # >>> [10, 20]

    # Bracket access is also supported
    config.meta['x'].tags       # >>> {'number'}

Instance-level metadata is independent across instances — modifying one instance's
metadata does not affect other instances or the class definition.

.. code-block:: python

    config_a = MyConfig()
    config_b = MyConfig()

    config_a.meta.x.variants.append(30)

    config_a.meta.x.variants    # >>> [10, 20, 30]
    config_b.meta.x.variants    # >>> [10, 20]  (unchanged)


---------------------------------------------
Type constraints
---------------------------------------------

Since ``Param`` forwards all keyword arguments to Pydantic's ``Field``, standard Pydantic
field constraints apply directly.

For **numeric ranges**, use ``ge`` (≥), ``le`` (≤), ``gt`` (>), ``lt`` (<):

.. code-block:: python

    class MyConfig(Configuration):
        x: int = Param(5, ge=1, le=10)     # 1 <= x <= 10

    MyConfig(x=5)   # ✓
    MyConfig(x=0)   # ✗ ValidationError

For **discrete allowed values**, use ``Literal``:

.. code-block:: python

    from typing import Literal

    class MyConfig(Configuration):
        mode: Literal['train', 'eval', 'test'] = Param('train')

    MyConfig(mode='train')  # ✓
    MyConfig(mode='other')  # ✗ ValidationError

For **cross-field constraints**, use ``@model_validator``:

.. code-block:: python

    from pydantic import model_validator

    class MyConfig(Configuration):
        x: int = Param(10)
        y: int = Param(5)

        @model_validator(mode='after')
        def check_x_greater_than_y(self) -> 'MyConfig':
            if self.x <= self.y:
                raise ValueError(
                    f'x must be greater than y, got x={self.x}, y={self.y}'
                )
            return self

    MyConfig(x=10, y=5)     # ✓
    MyConfig(x=3, y=5)      # ✗ ValidationError


=============================================
Configuration
=============================================

A ``Configuration`` is defined by subclassing ``Configuration`` and declaring fields
as typed class annotations:

.. code-block:: python

    class MyConfig(Configuration):
        x: int = Param(50, description='An example parameter')

    config = MyConfig()
    print(config.x)     # >>> 50

Field values are accessed as regular Python attributes.
Since ``Configuration`` validates defaults at instantiation (``validate_default=True``),
a misconfigured default is caught immediately:

.. code-block:: python

    class InvalidConfig(Configuration):
        x: int = Param(5, ge=1, le=3)

    InvalidConfig()     # ✗ ValidationError: x=5 violates le=3

To create a modified copy of an existing instance, use ``model_copy``:

.. code-block:: python

    config = MyConfig()
    updated = config.model_copy(update={'x': 10})

    print(updated.x)    # >>> 10
    print(config.x)     # >>> 50  (original unchanged)

``model_copy`` re-validates the updated fields, so constraints are enforced:

.. code-block:: python

    class MyConfig(Configuration):
        x: int = Param(5, ge=1, le=10)

    config = MyConfig()
    config.model_copy(update={'x': 99})     # ✗ ValidationError


---------------------------------------------
Accessing field values and definitions
---------------------------------------------

All field values are accessible as a plain dictionary via the ``values`` property:

.. code-block:: python

    class MyConfig(Configuration):
        x: int = Param(5)
        y: bool = Param(True)

    config = MyConfig()
    config.values   # >>> {'x': 5, 'y': True}

All ``FieldInfo`` definitions (type, default, constraints, metadata) are accessible
via the ``fields`` property, which mirrors ``model_fields``:

.. code-block:: python

    config.fields           # >>> {'x': FieldInfo(...), 'y': FieldInfo(...)}
    config.fields['x']      # >>> FieldInfo(default=5, ...)


---------------------------------------------
Adding conditions
---------------------------------------------

Beyond Pydantic's built-in field validation, ``Configuration`` supports runtime
**conditions**: arbitrary callables that check invariants across one or more fields.

.. code-block:: python

    class MyConfig(Configuration):
        x: int = Param(10)
        y: int = Param(5)

    config = MyConfig()
    config.add_condition(
        name='x_equals_y',
        condition=lambda c: c.x == c.y,
        description='x and y must be equal'
    )

The condition name must be unique. Registering a second condition with the same name
raises a ``RuntimeWarning``.

Conditions accept an optional ``tags`` set for grouping:

.. code-block:: python

    config.add_condition(
        name='x_positive',
        condition=lambda c: c.x > 0,
        tags={'sanity'},
        description='x must be positive'
    )

.. note::
    Conditions registered via ``add_condition`` are evaluated lazily — they are
    not checked at instantiation time. Use ``@model_validator`` for constraints
    that should be enforced at construction.


---------------------------------------------
Validating conditions
---------------------------------------------

Conditions registered via ``add_condition`` are evaluated explicitly by calling
``validate_conditions``:

.. code-block:: python

    class MyConfig(Configuration):
        x: int = Param(10)
        y: int = Param(5)

    config = MyConfig()
    config.add_condition(name='match', condition=lambda c: c.x == c.y)

    config.validate_conditions()                # ✗ raises ValidationFailureException
    config.validate_conditions(strict=False)    # returns ValidationResult(passed=False, ...)

    config = config.model_copy(update={'x': 5})
    config.add_condition(name='match', condition=lambda c: c.x == c.y)
    config.validate_conditions()                # ✓ passes silently

When ``strict=False``, a ``ValidationResult`` is returned instead of raising an exception,
allowing callers to inspect the result programmatically:

.. code-block:: python

    result = config.validate_conditions(strict=False)
    result.passed           # >>> False
    result.error_message    # >>> 'Condition match failed!'

If a ``Configuration`` has nested ``Configuration`` dependencies, ``validate_conditions``
recursively validates them as well.


---------------------------------------------
Searching fields by tag
---------------------------------------------

Tags allow quickly retrieving fields that share a keyword:

.. code-block:: python

    class MyConfig(Configuration):
        x: int  = Param(10,   tags={'number'})
        y: bool = Param(True, tags={'boolean'})
        z: int  = Param(30,   tags={'number'})

    config = MyConfig()

    number_fields = {
        name: config.meta[name]
        for name in config.fields
        if 'number' in config.meta[name].tags
    }
    # >>> {'x': ParamMeta(...), 'z': ParamMeta(...)}

To filter by multiple tags, extend the condition:

.. code-block:: python

    target_tags = {'number', 'hyperparameter'}
    matching = {
        name: config.meta[name]
        for name in config.fields
        if target_tags & config.meta[name].tags  # non-empty intersection
    }


=============================================
Default template
=============================================

``Configuration`` subclasses define their fields at class level — no explicit ``default()``
override is needed in the typical case.
The inherited ``default()`` classmethod is equivalent to calling the constructor with no
arguments:

.. code-block:: python

    class MyConfig(Configuration):
        x: int = Param(5)

    config = MyConfig.default()
    # equivalent to: config = MyConfig()
    config.x    # >>> 5

For configurations that require custom initialisation logic, ``default()`` can be overridden:

.. code-block:: python

    class MyConfig(Configuration):
        x: int = Param(5)

        @classmethod
        def default(cls) -> 'MyConfig':
            config = super().default()
            config.add_condition(
                name='x_positive',
                condition=lambda c: c.x > 0
            )
            return config

Inheritance works naturally — a subclass inherits all fields from its parent and may
add new ones:

.. code-block:: python

    class MyConfig(Configuration):
        x: int = Param(5)

    class MyConfigExtension(MyConfig):
        y: bool = Param(True)

    config = MyConfigExtension.default()
    config.x    # >>> 5  (inherited)
    config.y    # >>> True


=============================================
Variants
=============================================

Instead of defining multiple ``Configuration`` subclasses for slight parameter variations,
cinnamon supports **variants**: alternative values declared alongside a field's default.

.. code-block:: python

    class CustomConfig(Configuration):
        x: int  = Param(5,     variants=[20, 42])
        y: bool = Param(False, variants=[True])

The default value must **not** appear in ``variants`` — cinnamon enforces this at
instantiation and raises a ``ValidationError`` if a duplicate is detected.

The ``variants`` property returns all unique combinations of variant values, excluding
the all-default combination (which is the configuration itself):

.. code-block:: python

    config = CustomConfig.default()
    combos = config.variants

Each entry in the returned list is a dict with two keys:

- ``values``: the field values for this combination.
- ``indexes``: the index of each value within its field's variant list (``0`` = default).

.. code-block:: python

    # combos[0] = {'values': {'x': 5,  'y': True},  'indexes': {'x': 0, 'y': 1}}
    # combos[1] = {'values': {'x': 20, 'y': False}, 'indexes': {'x': 1, 'y': 0}}
    # combos[2] = {'values': {'x': 20, 'y': True},  'indexes': {'x': 1, 'y': 1}}
    # combos[3] = {'values': {'x': 42, 'y': False}, 'indexes': {'x': 2, 'y': 0}}
    # combos[4] = {'values': {'x': 42, 'y': True},  'indexes': {'x': 2, 'y': 1}}

Use ``model_copy`` to instantiate a specific variant:

.. code-block:: python

    variant = config.model_copy(update=combos[0]['values'])
    variant.x   # >>> 5
    variant.y   # >>> True


=============================================
Nesting (i.e., adding dependencies)
=============================================

``Configuration`` instances can be nested to compose more sophisticated configurations.
Nesting is expressed via ``RegistrationKey`` values — loose pointers resolved at
build time by the ``Registry``.

.. code-block:: python

    from cinnamon.registry import RegistrationKey

    class ChildConfig(Configuration):
        z: int = Param(42)

    class ParentConfig(Configuration):
        param_1: bool = Param(True,  variants=[False, True])
        param_2: bool = Param(False, variants=[False, True])
        child: RegistrationKey = Param(
            RegistrationKey(name='child', tags={'default'}, namespace='testing')
        )

The ``dependencies`` property returns all fields whose value is a ``RegistrationKey``
or a nested ``Configuration`` instance:

.. code-block:: python

    config = ParentConfig.default()
    config.dependencies
    # >>> {'child': RegistrationKey(name='child', tags={'default'}, namespace='testing')}

.. note::
    In cinnamon, nested configurations are called **dependencies**.
    See `dependencies <https://nlp-unibo.github.io/cinnamon/dependencies.html>`_
    for how the ``Registry`` resolves and builds them automatically.


.. toctree::
   :maxdepth: 4
   :hidden:
   :caption: Contents:
   :titlesonly: