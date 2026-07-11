from typing import Tuple

from cinnamon.configuration import Configuration, Param
from cinnamon.registry import Registry, register, register_method


class TfIdfProcessorConfig(Configuration):
    ngram_range: Tuple[int, int] = Param(
        (1, 1), description="Vectorizer ngram_range hyper-parameter"
    )

    @classmethod
    @register_method(
        name="processor",
        tags={"tf-idf"},
        namespace="examples",
        component="examples.components.processor.TfIdfProcessor",
    )
    def default(cls):
        config = super().default()
        return config


@register
def register_processors():
    Registry.register_configuration(
        config=Configuration.default(),
        component="examples.components.processor.LabelProcessor",
        name="processor",
        tags={"label"},
        namespace="examples",
    )
