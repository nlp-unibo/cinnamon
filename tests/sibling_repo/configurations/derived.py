from typing import Type

from cinnamon.configuration import C
from cinnamon.registry import register_method
from tests.sibling_repo.configurations.base import BaseConfig
from tests.sibling_repo.configurations.keys import NAMESPACE


class DerivedConfig(BaseConfig):
    @classmethod
    @register_method(
        name="derived",
        namespace=NAMESPACE,
        component="tests.fixtures.EmptyComponent",
    )
    def default(cls: Type[C]) -> C:
        return super().default()
