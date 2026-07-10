.. _commands:

Cinnamon entry points
*********************************************

Cinnamon ships three console scripts for working with ``Configuration`` and ``Component``
without writing boilerplate code.

=============================================
Installation
=============================================

The core ``cinnamon`` package does not include the interactive CLI dependency.
To use ``cmn-run`` and ``cmn-generate``, install the ``cli`` extra:

.. code-block:: bash

    pip install cinnamon[cli]

``cmn-build`` has no extra dependencies and works with the base install.

=============================================
Common arguments
=============================================

All three commands accept the same two optional arguments:

``-dir`` / ``--directory``
    Path to the main project directory containing the ``configurations`` folder.
    Defaults to the current working directory if not provided.

``-ext`` / ``--external-path``
    Path to a JSON file listing external project directories to include during
    registration. The file must contain a JSON array of path strings:

    .. code-block:: json

        [
            "/path/to/external/project_a",
            "/path/to/external/project_b"
        ]

    See `dependencies <https://nlp-unibo.github.io/cinnamon/dependencies.html>`_ for
    details on external directories.

=============================================
cmn-build
=============================================

``cmn-build`` is the console script equivalent of calling ``Registry.build()`` directly.
It scans the project's ``configurations`` folder, resolves all dependencies and variants,
and reports which ``RegistrationKey`` instances are valid or invalid.

.. code-block:: bash

    cmn-build

    # with explicit directory
    cmn-build --directory path/to/project

    # with external directories
    cmn-build --directory path/to/project --external-path path/to/externals.json

After a successful run, ``cmn-build`` writes two JSON files inside a ``registrations/``
folder in your project directory:

- ``valid_keys.json`` — all ``RegistrationKey`` instances that passed validation.
- ``invalid_keys.json`` — all keys that failed, along with the reason stored in
  ``RegistrationKey.metadata``.

Valid and invalid keys are also logged to the console at ``INFO`` level.

A ``RegistrationKey`` is **valid** if its bound ``Configuration`` passes all Pydantic
field constraints and all ``add_condition`` conditions after dependency resolution.
It is **invalid** if any constraint or condition fails, or if a required dependency
could not be found.


=============================================
cmn-run
=============================================

``cmn-run`` builds the registry and interactively guides you through selecting and
executing one or more registered runnable components.

.. code-block:: bash

    cmn-run

    # with explicit directory
    cmn-run --directory path/to/project

.. note::
    A ``Component`` is only available in ``cmn-run`` if it was registered with a
    ``run_method``. See the registration section below.

---------------------------------------------
Registering a runnable component
---------------------------------------------

A component becomes runnable by specifying ``run_method`` at registration time.
The method must take no arguments beyond ``self``:

.. code-block:: python

    from cinnamon.component import Component
    from cinnamon.configuration import Configuration, Param
    from cinnamon.registry import register_method

    class TrainerComponent(Component):

        def __init__(self, epochs: int, lr: float):
            self.epochs = epochs
            self.lr = lr

        def train(self):
            print(f'Training for {self.epochs} epochs at lr={self.lr}')

    class TrainerConfig(Configuration):
        epochs: int = Param(10)
        lr: float = Param(0.001)

        @classmethod
        @register_method(
            name='trainer',
            tags={'default'},
            namespace='my_project',
            component='components.TrainerComponent',
            run_method='train'
        )
        def default(cls) -> 'TrainerConfig':
            return super().default()

---------------------------------------------
Interactive selection
---------------------------------------------

``cmn-run`` guides you through four sequential prompts to narrow down and confirm
the components to run:

1. **Namespace** — if more than one namespace is registered, select one from the list.
   If only one exists, it is selected automatically.
2. **Name** — select a ``RegistrationKey`` name from the filtered list.
   Choose *Cancel* to restart.
3. **Tags** — iteratively add tags to narrow the selection. Choose *Proceed* once
   the desired subset is reached, *Go back* to remove the last tag, or *Cancel*
   to restart.
4. **Final selection** — a checkbox list of all matching keys. At least one must
   be selected.

After confirming the selection, ``cmn-run`` builds each chosen component and invokes
its ``run_method`` in sequence. The bound ``Configuration``'s field values are logged
via ``model_dump()`` before each run.


=============================================
cmn-generate
=============================================

``cmn-generate`` builds the registry, guides you through the same interactive
key selection as ``cmn-run``, and writes a self-contained Python script that
runs the selected components without requiring the CLI.

.. code-block:: bash

    cmn-generate --filename my_experiment

    # with explicit directories
    cmn-generate \
        --directory path/to/project \
        --run-directory path/to/output \
        --filename my_experiment

``cmn-generate`` accepts two additional arguments:

``-run-dir`` / ``--run-directory``
    Directory where the generated script is written.
    Defaults to the current working directory.

``-name`` / ``--filename`` *(required)*
    Name of the generated Python file (without the ``.py`` extension).

The generated script contains the selected ``RegistrationKey`` strings, calls
``Registry.build()``, then retrieves and runs each component in sequence.
If a script with the given filename already exists in the target directory,
``cmn-generate`` will prompt you before overwriting it.

.. note::
    The generated script itself only requires the
    base ``cinnamon`` install.


.. toctree::
   :maxdepth: 4
   :hidden:
   :caption: Contents:
   :titlesonly: