from pathlib import Path

from cinnamon.configuration import Configuration, Param
from cinnamon.registry import register_method


class IMDBLoaderConfig(Configuration):
    download_directory: Path = Param(
        Path(__file__).resolve().parent.parent.joinpath("datasets"),
        description="Folder the archive file is downloaded",
    )
    download_filename: str = Param(
        "imdb.tar.gz", description="Name of the archive file"
    )
    dataset_name: str = Param("dataset.csv", description="Name of the dataset file")
    download_url: str = Param(
        "http://ai.stanford.edu/~amaas/data/sentiment/aclImdb_v1.tar.gz",
        description="URL to dataset archive file",
    )
    samples_amount: int = Param(
        500, description="Number of samples per split to consider at maximum"
    )

    @classmethod
    @register_method(
        name="data_loader",
        tags={"imdb"},
        namespace="examples",
        component="examples.components.IMDBLoader",
        run_method="load_data",
    )
    def default(cls):
        config = super().default()
        return config
