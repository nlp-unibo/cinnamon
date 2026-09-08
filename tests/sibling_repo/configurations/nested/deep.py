from typing import Type

from cinnamon.configuration import C, Configuration
from cinnamon.registry import register_method
from tests.sibling_repo.configurations.keys import NAMESPACE


class DeepConfig(Configuration):
    @classmethod
    @register_method(
        name="deep",
        namespace=NAMESPACE,
        component="tests.fixtures.EmptyComponent",
    )
    def default(cls: Type[C]) -> C:
        return super().default()
