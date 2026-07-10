import logging
from logging import getLogger
from pathlib import Path

from cinnamon.registry import Registry
from examples.components.data_loader import IMDBLoader

if __name__ == "__main__":
    """
    In this demo script, we retrieve and build our IMDB data loader.
    Once built, we run the data loader to load the IMDB dataset and
     print it for visualization purposes.
    """

    directory = Path(__file__).parent.parent.resolve()
    Registry.build(directory=directory)
    logging.basicConfig()
    logger = getLogger(__name__)

    loader = IMDBLoader.instantiate(
        name="data_loader", tags={"imdb"}, namespace="examples"
    )
    df = loader.load_data()
    print(df)
