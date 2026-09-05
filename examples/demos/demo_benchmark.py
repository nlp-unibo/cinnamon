import logging
from logging import getLogger
from pathlib import Path

from cinnamon.registry import Registry

if __name__ == "__main__":
    """
    In this demo script, we retrieve and build our SVC pipeline.
    The pipeline covers data loading, data processing, and model evaluation.
    """

    directory = Path(__file__).parent.parent.resolve()
    Registry.build(directory=directory)
    logging.basicConfig(level=logging.INFO)
    logger = getLogger(__name__)

    benchmark = Registry.instantiate(
        name="benchmark", tags={"svc"}, namespace="examples"
    )
    benchmark.run()
