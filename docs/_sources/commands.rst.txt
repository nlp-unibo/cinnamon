.. _commands:

Cinnamon entry points
*********************************************

The cinnamon package offers console scripts to work with ``Configuration`` and ``Component`` without requiring any custom code.

=============================================
cmn-setup
=============================================

The ``cmn-setup`` command is the console script version of ``Registry.setup()``.

In addition to loading registrations and resolving dependencies, the ``cmn-setup`` command stores in csv format all valid and invalid ``RegistrationKey``.

In particular, a ``RegistrationKey`` is valid (invalid) if the associated ``Configuration`` instance is valid (invalid).

To run ``cmn-setup``, do as follows

.. code-block:: bash

    cmn-setup --dir *main-directory* --ext *ext-directory-1* *ext-directory-2* ...

By default, ``cmn-setup`` takes ``dir=pwd``.

Thus, usually, we only require to open a terminal in our main project directory and run

.. code-block:: bash

    cmn-setup

=============================================
cmn-run
=============================================

The ``cmn-run`` command allows building and executing ``Component`` given a ``RegistrationKey``.

In particular, there exist a specific extension of ``Component``, denoted as ``RunnableComponent`` that adds the ``run()`` method.

Thus, to transform a ``Component`` into a ``RunnableComponent``, we only need to define some code logic under ``run()``.

For instance,

.. code-block:: python

    class CustomRunnable(cinnamon.component.RunnableComponent):

        def __init__(self, x, y):
            self.x = x
            self.y = y

        def run(
            config: cinnamon.configuration.Configuration
        ):
            print(f"Running this component with x={x} and y={y}")
            print(f'The configuration of the component is {config})

Defines a simple ``RunnableComponent`` that prints some information when being executed.

Given a ``RegistrationKey``, the ``cmn-run`` does the following:

- Retrieves from ``Registry`` the ``Configuration`` info via the given ``RegistrationKey``
- Builds a ``Configuration`` instance
- Builds a ``Component`` instance by providing the built ``Configuration`` parameters.

Nonetheless, providing a ``RegistrationKey`` by heart is not a simple task, especially as projects scale up in the number of defined ``Configuration`` and ``Component``.

To account for this problem, ``cmn-run`` allows for interactive search for ``RegistrationKey`` by relying on `InquirePy <https://inquirerpy.readthedocs.io/en/latest/>`_.

In particular, ``cmn-run`` guides the user through three distinct prompts:

1. ``namespace`` selection
2. ``name`` selection
3. ``tags`` selection

Eventually, the defined ``RegistrationKey`` might be compatible with several actually registered ``RegistrationKey``.

Thus, ``cmn-run`` allows selecting one or more of those keys to execute all corresponding components in sequence.

.. note::
    Intuitively, ``cmn-run`` supports running one or more ``RunnableComponent`` in sequence given a ``name``, some ``tags`` and a ``namespace``.


.. toctree::
   :maxdepth: 4
   :hidden:
   :caption: Contents:
   :titlesonly:


