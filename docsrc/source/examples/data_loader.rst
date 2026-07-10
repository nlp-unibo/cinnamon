.. _data_loader:

Loading data with ``DataLoader``
*************************************

We consider the **IMDB** dataset for this example.

We first define our custom ``IMDBLoader`` component.

Then, we define its associated ``IMDBLoaderConfig`` configuration and perform registrations.

Lastly, we define the runnable script to run our ``IMDBLoader`` and check loaded data.

------------------
``IMDBLoader``
------------------

.. code-block:: python

    class IMDBLoader(RunnableComponent):

        def __init__(
                self,
                download_directory: Path,
                download_filename: str,
                dataset_name: str,
                download_url: str,
                samples_amount: int = -1
        ):
            self.download_directory = download_directory
            self.download_filename = download_filename
            self.dataset_name = dataset_name
            self.download_url = download_url
            self.samples_amount = samples_amount

            self.download_path = download_directory.joinpath(download_filename)
            self.extraction_path = self.download_path.parents[0]
            self.dataframe_path = self.extraction_path.joinpath(dataset_name)

        def download(
                self
        ):
            if not self.download_directory.exists():
                self.download_directory.mkdir(parents=True)

            # Download
            if not self.download_path.exists():
                download_url(url=self.download_url, download_path=self.download_path)

                # Extract
                with tarfile.open(self.download_path) as loaded_tar:
                    loaded_tar.extractall(self.extraction_path)

            # Clean
            if self.download_path.exists():
                self.download_path.unlink()

        def read_df_from_files(
                self
        ) -> pd.DataFrame:
            dataframe_rows = []
            for split in ['train', 'test']:
                for sentiment in ['pos', 'neg']:
                    folder = self.extraction_path.joinpath('aclImdb', split, sentiment)
                    for filepath in folder.glob('**/*'):
                        if not filepath.is_file():
                            continue

                        filename = filepath.name
                        with filepath.open(mode='r', encoding='utf-8') as text_file:
                            text = text_file.read()
                            score = filename.split("_")[1].split(".")[0]
                            file_id = filename.split("_")[0]

                            # create single dataframe row
                            dataframe_row = {
                                "file_id": file_id,
                                "score": score,
                                "sentiment": sentiment,
                                "split": split,
                                "text": text
                            }
                            dataframe_rows.append(dataframe_row)

            df = pd.DataFrame(dataframe_rows)
            df = df[["file_id",
                     "score",
                     "sentiment",
                     "split",
                     "text"]]
            df = df.rename(columns={'sentiment': 'y', 'text': 'x'})

            # Save dataframe for quick retrieval
            df.to_csv(path_or_buf=self.dataframe_path, index=None)

            return df

        def load_data(
                self
        ) -> pd.DataFrame:
            if not self.dataframe_path.is_file():
                print('First time loading dataset...Downloading...')
                self.download()
                df = self.read_df_from_files()
            else:
                if self.dataframe_path.is_file():
                    print('Loaded pre-loaded dataset...')
                    df = pd.read_csv(self.dataframe_path)
                else:
                    print("Couldn't find pre-loaded dataset...Building dataset from files...")
                    df = self.read_df_from_files()
                    df.to_csv(self.dataframe_path, index=False)

            return df

        def get_splits(
                self,
        ) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame], Optional[pd.DataFrame]]:
            df = self.load_data()
            train = df[df.split == 'train'].sample(frac=1).reset_index(drop=True)[:self.samples_amount]
            val = None
            test = df[df.split == 'test'].sample(frac=1).reset_index(drop=True)[:self.samples_amount]

            return train, val, test

        def run(
                self,
                config: Optional[cinnamon.configuration.Configuration] = None
        ):
            return self.load_data()


The ``IMDBLoader`` does the following:

- ``download``: checks if the dataset has to be downloaded from the web. If yes, the loader downloads it and extracts the archive file.
- ``read_df_from_files``: an internal utility function that reads extracted files to build a ``pandas.DataFrame`` view of the IMDB dataset.
- ``load_data``: the API to invoke to obtain the ``pandas.DataFrame`` of the dataset.
- ``get_splits``: retrieves the train, validation and test data splits, if available.
- ``run``: runs ``load_data`` and returns the resulting ``pandas.DataFrame``. The ``run`` method defines the entry point for running ``IMDBLoader`` via command line.


-------------------------
``IMDBLoaderConfig``
-------------------------

The ``IMDBLoader`` uses ``IMDBLoaderConfig`` as default configuration template.

.. code-block:: python

    class IMDBLoaderConfig(Configuration):

        @classmethod
        @register_method(name='data_loader',
                         tags={'imdb'},
                         namespace='examples',
                         component_class=IMDBLoader)
        def default(
                cls
        ):
            config = super().default()

            config.add(name='download_directory',
                       value=Path(__file__).resolve().parent.parent.joinpath('datasets'),
                       type_hint=Path,
                       description='Folder the archive file is downloaded')
            config.add(name='download_filename',
                       value='imdb.tar.gz',
                       type_hint=str,
                       description='Name of the archive file')
            config.add(name='dataset_name',
                       value='dataset.csv',
                       type_hint=str,
                       description='.csv filename')
            config.add(name='download_url',
                       value='http://ai.stanford.edu/~amaas/data/sentiment/aclImdb_v1.tar.gz',
                       type_hint=Union[AnyStr, Path],
                       description='URL to dataset archive file')
            config.add(name='samples_amount',
                       value=500,
                       type_hint=int,
                       description='Number of samples per split to consider at maximum')

            return config


Note that we **register** the default template via ``RegistrationKey`` (``name=data_loader``, ``tags={'imdb'}``, ``namespace=examples``) and bind it to ``IMDBLoader`` component.

----------------------------
Running ``IMDBLoader``
----------------------------

We can now write a script to test ``IMDBLoader``.

.. code-block:: python

    from pathlib import Path

    from cinnamon.registry import Registry
    from components.data_loader import IMDBLoader

    if __name__ == '__main__':
        """
        In this demo script, we retrieve and build our IMDB data loader.
        Once built, we run the data loader to load the IMDB dataset and print it for visualization purposes.
        """

        directory = Path(__file__).parent.parent.resolve()
        Registry.setup(directory=directory)

        loader = IMDBLoader.build_component(name='data_loader',
                                            tags={'imdb'},
                                            namespace='examples')
        df = loader.load_data()
        print(df)

----------------
Next!
----------------

That's it! We have defined our data loader component to load and parse the IMDB dataset.

Next, we define data ``Processor`` to further parse our input data for our classifier.