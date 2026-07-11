.. _examples_overview:

Overview
=============================================

The examples folder contains a complete machine-learning pipeline built with cinnamon.
It is a good starting point to see how ``Component`` and ``Configuration`` work together
in a real project.

The pipeline covers:

- A ``DataLoader`` that downloads and parses the IMDB dataset.
- Two ``Processor`` components — one for tf-idf features, one for label encoding.
- An ``SVCModel`` wrapping scikit-learn's SVC classifier.
- An ``SVCBenchmark`` that wires everything together and evaluates the model.

All components are registered in the ``Registry`` and can be swapped independently.

=============================================
Project layout
=============================================

.. code-block::

    examples/
        components/
            data_loader.py      ← IMDBLoader
            processor.py        ← TfIdfProcessor, LabelProcessor
            model.py            ← SVCModel
            benchmark.py        ← SVCBenchmark
        configurations/
            data_loader.py      ← IMDBLoaderConfig
            processor.py        ← TfIdfProcessorConfig, LabelProcessor registration
            model.py            ← SVCModelConfig
            benchmark.py        ← SVCBenchmarkConfig
        demos/
            demo_data_loader.py ← run IMDBLoader standalone
            demo_benchmark.py   ← run the full pipeline


=============================================
Installation
=============================================

Install cinnamon and the example dependencies:

.. code-block:: bash

    pip install "cinnamon[examples]"

=============================================
Running the demos
=============================================

Run the full benchmark pipeline:

.. code-block:: bash

    cd examples
    python demos/demo_benchmark.py

Run only the data loader:

.. code-block:: bash

    cd examples
    python demos/demo_data_loader.py

Both scripts call ``Registry.build()`` to discover and register all configurations
under the ``configurations/`` folder before building the components.

=============================================
Using these components in your own project
=============================================

You can reuse the example components and configurations from your own project by
pointing ``Registry.build()`` to the examples folder as an external directory:

.. code-block:: python

    from pathlib import Path
    from cinnamon.registry import Registry

    Registry.build(
        directory=Path('.'),                           # your project
        external_directories=[Path('path/to/examples')]
    )

Once built, you can register configurations that reference the example keys:

.. code-block:: python

    from cinnamon.configuration import Configuration, Param
    from cinnamon.registry import RegistrationKey, register_method

    class CustomBenchmarkConfig(Configuration):
        data_loader: RegistrationKey = Param(
            RegistrationKey(name='data_loader', tags={'imdb'}, namespace='examples')
        )
        model: RegistrationKey = Param(
            RegistrationKey(name='model', tags={'svc'}, namespace='examples')
        )

        @classmethod
        @register_method(name='benchmark', tags={'custom'}, namespace='my_project',
                         component='components.CustomBenchmark', run_method='run')
        def default(cls) -> 'CustomBenchmarkConfig':
            return super().default()

.. note::
    Make sure to install the example dependencies before importing example components,
    otherwise the import will fail during ``Registry.build()``.