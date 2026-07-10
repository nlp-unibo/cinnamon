import logging
from logging import getLogger
from pathlib import Path

from cinnamon.registry import Registry
from examples.components.benchmark import SVCBenchmark

if __name__ == "__main__":
    """
    In this demo script, we retrieve and build our SVC pipeline.
    The pipeline covers data loading, data processing, and model evaluation.
    """

    directory = Path(__file__).parent.parent.resolve()
    Registry.build(directory=directory)
    logging.basicConfig()
    logger = getLogger(__name__)

    benchmark = SVCBenchmark.instantiate(
        name="benchmark", tags={"svc"}, namespace="examples"
    )
    benchmark.run()
