from typing import Type

from cinnamon.configuration import C, Configuration
from cinnamon.registry import register_method


class MockConfiguration(Configuration):
    @classmethod
    @register_method(
        name="config",
        tags={"nest2"},
        namespace="testing",
        component="cinnamon.component.Component",
    )
    @register_method(
        name="config",
        tags={"nest1"},
        namespace="testing",
        component="cinnamon.component.Component",
    )
    def default(cls: Type[C]) -> C:
        return cls()
