.. _data_loader:

Data Loader
*************************************

The first step of the pipeline is loading the IMDB dataset from disk (or downloading
it if not yet available).

=============================================
``IMDBLoader``
=============================================

``IMDBLoader`` inherits from ``Component`` and handles downloading, extracting,
and parsing the IMDB archive into a ``pandas.DataFrame``:

.. code-block:: python

    class IMDBLoader(Component):

        def __init__(
            self,
            download_directory: Path,
            download_filename: str,
            dataset_name: str,
            download_url: str,
            samples_amount: int = -1,
        ):
            self.download_directory = download_directory
            self.download_filename = download_filename
            ...
            self.dataframe_path = self.extraction_path.joinpath(dataset_name)

        def download(self): ...

        def load_data(self) -> pd.DataFrame:
            """Download if needed, then return the dataset as a DataFrame."""
            ...

        def get_splits(self) -> Tuple[DataFrame, None, DataFrame]:
            """Return (train, val=None, test) splits."""
            df = self.load_data()
            train = df[df.split == 'train'].sample(frac=1)[:self.samples_amount]
            test  = df[df.split == 'test' ].sample(frac=1)[:self.samples_amount]
            return train, None, test

The key methods are:

- ``download()`` — checks whether the archive needs downloading; downloads and extracts it if so; cleans up the archive afterwards.
- ``load_data()`` — returns the full dataset as a ``DataFrame``, using a cached CSV if available.
- ``get_splits()`` — returns shuffled train and test splits, capped at ``samples_amount`` rows each. The validation split is ``None`` in this example.

=============================================
``IMDBLoaderConfig``
=============================================

.. code-block:: python

    class IMDBLoaderConfig(Configuration):
        download_directory: Path = Param(
            Path(__file__).resolve().parent.parent.joinpath('datasets'),
            description='Folder the archive file is downloaded into'
        )
        download_filename: str = Param(
            'imdb.tar.gz',
            description='Name of the archive file'
        )
        dataset_name: str = Param(
            'dataset.csv',
            description='Name of the cached CSV file'
        )
        download_url: str = Param(
            'http://ai.stanford.edu/~amaas/data/sentiment/aclImdb_v1.tar.gz',
            description='URL to the dataset archive'
        )
        samples_amount: int = Param(
            500,
            description='Maximum number of samples per split (-1 = all)'
        )

        @classmethod
        @register_method(
            name='data_loader',
            tags={'imdb'},
            namespace='examples',
            component='examples.components.data_loader.IMDBLoader',
            run_method='load_data'
        )
        def default(cls) -> 'IMDBLoaderConfig':
            return super().default()

Each field maps directly to a parameter of ``IMDBLoader.__init__``.
The ``run_method='load_data'`` binding means ``cmn-run`` and ``cmn-ui``
will call ``loader.load_data()`` when this key is selected for execution.

=============================================
Demo script
=============================================

.. code-block:: python

    from pathlib import Path
    from cinnamon.registry import Registry
    from examples.components.data_loader import IMDBLoader

    if __name__ == '__main__':
        directory = Path(__file__).parent.parent.resolve()
        Registry.build(directory=directory)

        loader = IMDBLoader.instantiate(
            name='data_loader', tags={'imdb'}, namespace='examples'
        )
        df = loader.load_data()
        logging.info(df)

``Registry.build()`` scans the ``configurations/`` folder, registers all keys,
and resolves dependencies. ``IMDBLoader.instantiate()`` then retrieves the registered
``IMDBLoaderConfig``, unpacks its values, and constructs the ``IMDBLoader`` instance.

.. note::
    The demo script is at ``examples/demos/demo_data_loader.py``.
    Run it from the ``examples/`` directory so relative paths resolve correctly.