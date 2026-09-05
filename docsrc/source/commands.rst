.. _commands:

Cinnamon entry points
*********************************************

Cinnamon ships four console scripts for working with configurations and components
without writing boilerplate code.

=============================================
Installation
=============================================

The core ``cinnamon`` package does not include the interactive CLI dependency.
To use ``cmn-run`` and ``cmn-generate``, install the ``cli`` extra:

.. code-block:: bash

    pip install cinnamon[cli]

``cmn-build`` and ``cmn-check`` have no extra dependencies and work with the
base install.

=============================================
Common arguments
=============================================

All four commands accept the same two optional arguments:

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

    See :doc:`dependencies` for details on external directories.

=============================================
cmn-check
=============================================

``cmn-check`` reports registration problems without running anything. It is the
cheapest thing to run after editing configurations, and it is designed to be usable
as a pre-commit or CI gate: it exits non-zero when it finds errors.

.. code-block:: bash

    cmn-check -dir .
    cmn-check -dir . --strict     # warnings fail too
    cmn-check -dir . --deep       # also import components to check signatures

It makes two passes.

**Keys.** Every dependency that resolves to nothing is reported *at once*, with the
registrations that reference it and a ranked suggestion of what you probably meant:

.. code-block:: text

    [error] unresolved-key
      No configuration is registered under name=loader--tags=['imbd']--namespace=nlp.
      referenced by:
        - name=pipeline--namespace=nlp
      did you mean:
        - name=loader--tags=['imdb']--namespace=nlp
            (tag 'imbd' -> 'imdb')

``Registry.build`` stops at the first missing key, so a project with three typos
would otherwise take three runs to fix. It also warns about tags that differ only
slightly from each other — ``tf-idf`` against ``tfidf``, ``IMDB`` against ``imdb`` —
which resolve perfectly well today and are pure latent confusion.

**Indexed variants.** A variant of a list or a dict is tagged by position --
``losses=variant-1`` -- because a container has no short stable rendering. The
index is deterministic, so keys stay comparable across runs, but it does not say
what is in the variant. ``cmn-check`` spells each one out, once per
configuration rather than once per key:

.. code-block:: text

    === Indexed Variants ===

      model (ns=nlp)
          losses=variant-1   = [ce, sparsity]
          losses=variant-2   = []
          metrics=variant-1  = {acc: acc, f1: f1}

**Bindings.** Component paths are resolved on the filesystem *without importing
them*, so the command stays fast whatever your components weigh. ``--deep`` imports
each one and checks its ``__init__`` against the configuration's fields, at the cost
of that import.

.. note::
    The shallow pass is deliberately modest. A missing top-level package is an
    error; a middle segment that is not a module is only a warning, because a wrong
    module path and a nested class are indistinguishable on disk. Whether the class
    exists inside the module is not checked at all — re-export is the norm, and many
    packages define no classes in the ``__init__.py`` you would be looking at.

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

- ``valid_keys.json`` — every key that passed validation.
- ``invalid_keys.json`` — every key that failed, each with the reason it did.

Both hold objects rather than strings, so a consumer reads fields instead of
parsing a line, and :meth:`~cinnamon.registry.RegistrationKey.from_dict` reads
them straight back:

.. code-block:: json

    [
      {
        "name": "model",
        "namespace": "nlp",
        "tags": ["learning_rate=0.01"]
      }
    ]

Entries in ``invalid_keys.json`` carry an extra ``reason`` field describing the
constraint or condition that rejected them.

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

    from cinnamon.configuration import Configuration, Param
    from cinnamon.registry import register_method

    class TrainerComponent:

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