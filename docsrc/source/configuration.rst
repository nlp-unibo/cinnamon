.. _configuration:

Configuration
*********************************************

=============================================
Param
=============================================

A ``Param`` is a useful wrapper for storing additional metadata like

- type hints
- textual descriptions
- allowed value range
- possible value variants
- optional tags for efficient ``Param`` search

For instance, the following code defines an integer ``Param`` with a specific allowed value range

.. code-block:: python

    param = Param(name='x', value=5, type_hint=int, allowed_range=lambda p: p in [1, 5, 10])


The ``name`` attribute is the ``Param`` unique identifier.

The ``allowed_range`` attribute introduces a condition such that ``x`` can only be set to ``1,``, ``5`` or ``10``.

Once set, a ``Param`` can be modified directly

.. code-block:: python

    param = Param(name='x', value=5, type_hint=int, allowed_range=lambda p: p in [1, 5, 10])
    print(param.value)      # >>> 5
    param.value = 10
    print(param.value)      # >>> 10

 The same applies for all other attributes of ``Param``.

=============================================
Configuration
=============================================

A ``Configuration`` stores all the parameters of a ``Component``.

.. image:: img/configuration.png
    :scale: 70%
    :align: center

Each parameter is wrapped into a ``Param``.

.. image:: img/configuration_params.png
    :scale: 60%
    :align: center

For example, we can define a ``Configuration`` inline with a ``Param`` as follows

.. code-block:: python

    config = Configuration()
    config.add(name='x', value=50, type_hint=int, description='An example parameter')
    print(config.x)     # >>> 50
    config.x = 10
    print(config.x)     # >>> 10

We can always access the ``Param`` instance via ``config.get()`` as follows

.. code-block:: python

    config = Configuration()
    config.add(name='x', value=50, type_hint=int, description='An example parameter')
    config.get('x').value = 20
    print(config.x)     # >>> 20
    config.get('x').variants = [10, 5, 70]

Adding a ``Param`` with via ``name`` that already exist will throw an error

.. code-block:: python

    config = Configuration()
    config.add(name='x', value=10)
    config.add(name='x', value=True)    # >>> raises cinnamon.AlreadyExistingParameterException

Likewise, setting a non-existing ``Param`` will throw an error

.. code-block:: python

    config = Configuration()
    config.add(name='x', value=10)
    config.y = True     # >>> raises AttributeError

---------------------------------------------
Adding conditions
---------------------------------------------

``Configuration`` also support special kind of ``Param`` known as **conditions**.

.. note::
    Therefore, all ``Param`` rules apply to conditions as well, such as conflicting names.

Conditions allow a user to set constraints on a ``Configuration``, such as enforcing a specific ``Param`` combination.

Some conditions are set under the hood when adding a ``Param``

.. code-block:: python

    config = Configuration()
    config.add(name='x', value=5, allowed_range: lambda v: v >= 0)
    config.add(name='y', is_required=True)

Here, we set two different **conditions**.

- ``allowed_range``: specifies that ``x`` can only be greater or equal than 0
- ``is_required``: specifies that ``y`` cannot be set to ``None``

We can also write our own conditions

.. code-block:: python

    config = Configuration()
    config.add(name='x', value=10)
    config.add(name='y', value=5)
    config.add_condition(name='match_x_y', condition=lambda c: c.x == c.y)

Here we specify that we only allow ``config`` to have ``x`` equal to ``y``.

.. note::
    So far, we have only defined conditions.
    We require now some APIs to **validate** such conditions to ensure that ``Configuration`` instances can be used.

---------------------------------------------
Validating Configurations
---------------------------------------------

``Configuration`` conditions are **not** executed **automatically**.

We can directly evaluate all conditions via ``Configuration.validate`` method

.. code-block:: python

    config = Configuration()
    config.add(name='x', value=10, variants=[5, 15])
    config.add(name='y', value=5, variants[10, 15])
    config.add_condition(name='match_x_y', condition=lambda c: c.x == c.y)
    config.validate()               # >>> raises cinnamon.ValidationFailureException
    config.validate(strict=False)   # >>> False

    config.x = 5
    config.validate()       # nothing happens, all conditions pass


---------------------------------------------
Search Params
---------------------------------------------

``Param`` support tags, a **set** of arbitrary string keywords provided by users.

Tags allow to quickly retrieve ``Param`` that share one or more keywords from a ``Configuration``

.. code-block:: python

    config = Configuration()
    config.add(name='x', value=10, tags={"number"})
    config.add(name='y', value=True, tags={"boolean"})
    config.add(name='z', value=30, tags={"number"})

    config.search_param_by_tag(tags='number')   # >>> [x, z]

``Param`` search can also be generalized based on custom conditions

.. code-block:: python

    config = Configuration()
    config.add(name='x', value=10, tags={"number"})
    config.add(name='y', value=True, tags={"boolean"})
    config.add(name='z', value=30, tags={"number"})

    config.search_param(conditions=[
        lambda param: 'number' in param.tags
    ])
    # >>> [x, z]


*********************************************
Delta copy
*********************************************

In many cases, we may need a slightly modified ``Configuration`` instance.

We can quickly create a ``Configuration`` instance delta copy by only specifying the parameters to change

.. code-block:: python

    config = Configuration()
    config.add(name='x', value=5)
    delta_copy = config.delta_copy(x=20)
    delta_copy.x    # >>> 20
    config.x        # >>> 5

We have created a delta copy of ``Configuration`` instance with ``x`` set to 20 instead of 5.

*********************************************
Default template
*********************************************

``Configuration`` are usually not defined inline as shown in the previous examples, but through class methods.

In particular, the ``default`` method defines the default template for ``Configuration``.

.. code-block:: python

    class MyConfig(cinnamon.configuration.Configuration):

        @classmethod
        def default(cls):
            config = super(cls).default()

            config.add(name='x', value=5)

            return config


    if __name__ == '__main__':
        config = MyConfig.default()
        config.x    # >>> 5

As any class, we can define custom template methods

.. code-block:: python

        class MyConfig(cinnamon.configuration.Configuration):

            @classmethod
            def default(cls):
                config = super(cls).default()

                config.add(name='x', value=5)

                return config

            @classmethod
            def custom_template(cls):
                config = cls.default()

                config.x = 20
                config.add(name='y', value=True)

                return config

Intuitively, since we are dealing with python classes, we can exploit inheritance to quickly define configuration extensions

.. code-block:: python

        class MyConfig(cinnamon.configuration.Configuration):

            @classmethod
            def default(cls):
                config = super(cls).default()

                config.add(name='x', value=5)

                return config

        class MyConfigExtension(MyConfig):

           @classmethod
           def default(cls):
               config = super(cls).default()

               config.add(name='y', value=True)

               return config


*********************************************
Variants
*********************************************

In a project, we may have that a ``Component`` is bound to several ``Configuration``.

In some of these cases, each of these ``Configuration`` are just slight parameter variations of a single ``Configuration`` template.

.. code-block:: python

    class CustomComponent(cinnamon.component.Component):

        def __init__(self, x, y):
            self.x = x
            self.y = y

    class CustomConfig(cinnamon.configuration.Configuration):

        @classmethod
        def default(cls):
            config = super(cls).default()

            config.add(name='x', value=5)
            config.add(name='y', value=True)

            return config

        @classmethod
        def variantA(cls):
            config = cls.default()

            config.x = 20
            config.y = False

            return config

        @classmethod
        def variantB(cls):
            config = cls.default()

            config.x = 42
            config.y = True

            return config

        @classmethod
        def variantC(cls):
            config = cls.default()

            # This is allowed since there is no condition prohibiting so
            config.x = [1, 2, 3]

            return config



In cinnamon, we can avoid explicitly defining all these ``Configuration`` templates and relying on the notion of **configuration variant**.

A configuration variant is a ``Configuration`` template that has at least one different parameter value.

We define variants by specifying the ``variants`` field when adding a parameter to the ``Configuration``.

.. code-block:: python

    class CustomConfig(cinnamon.configuration.Configuration):

        @classmethod
        def default(
                cls
        ):
            config = super().default()

            config.add(name='x',
                       value=5,
                       variants=[20, 42, [1, 2, 3]])
            config.add(name='y',
                       value=False,
                       variants=[True])
            return config

In the above code example, ``CustomConfig`` has ``x`` and ``y`` boolean parameters.
Both of them specify value variants, thus, defining 8 different ``CustomConfig`` variants, one for each combination of the two parameters.

We can quickly inspect these variants via ``Configuration.variants`` property.

.. code-block:: python

    config = MyConfig.default()
    variants = config.variants[0]
    # >>> variants[0] = {'x': 5, 'y': False}
    # >>> variants[1] = {'x': 5, 'y': True}
    # >>> variants[2] = {'x': 20, 'y': False}
    # >>> variants[3] = {'x': 20, 'y': True}
    # >>> variants[4] = {'x': 42, 'y': False}
    # >>> variants[5] = {'x': 42, 'y': True}
    # >>> variants[6] = {'x': [1, 2, 3], 'y': False}
    # >>> variants[7] = {'x': [1, 2, 3], 'y': True}

By using ``Configuration.delta_copy`` we can quickly instantiate one of these variants

.. code-block:: python

    my_variant = config.delta_copy(**variants[0])
    my_variant.x      # >>> 5
    my_variant.y      # >>> False

*********************************************
Nesting (i.e., adding dependencies)
*********************************************

One core functionality of cinnamon is that ``Configuration`` can be nested to build more sophisticated ones (the same applies for ``Component``).

Cinnamon does that via loose pointers called ``RegistrationKey``, a compound unique identifier associated to a specific ``Configuration``.

.. code-block:: python

    class ParentConfig(cinnamon.configuration.Configuration):

        @classmethod
        def default(
                cls
        ):
            config = super(cls).default()

            config.add(name='param_1',
                       value=True,
                       type_hint=bool,
                       variants=[False, True])
            config.add(name='param_2',
                       value=False,
                       type_hint=bool,
                       variants=[False, True])
            config.add(name='child',
                       value=RegistrationKey(name='test', tags={'nested'}, namespace='testing'))
            return config


    class NestedChild(Configuration):

        @classmethod
        def default(
                cls
        ):
            config = super().default()

            config.add(name='child',
                       value=RegistrationKey(name='test', tags={'plain'}, namespace='testing'),

            return config

In the above example, ``ParentConfig`` has a child ``Configuration``, named ``child``, pointing to ``NestedChild``.
Likewise, ``NestedChild`` has a child ``Configuration``, named ``child``.

.. note::
    In ``cinnamon`` nested configurations are called **dependencies**.
    You can access to a ``Configuration`` dependencies via ``Configuration.dependencies`` property.
