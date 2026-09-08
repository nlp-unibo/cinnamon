from typing import Type

from cinnamon.configuration import C, Configuration
from cinnamon.registry import register_method
from tests.sibling_repo.configurations.keys import NAMESPACE


class BaseConfig(Configuration):
    @classmethod
    @register_method(
        name="base",
        namespace=NAMESPACE,
        component="tests.fixtures.EmptyComponent",
    )
    def default(cls: Type[C]) -> C:
        return super().default()


class ExtraConfig(BaseConfig):
    """Not imported by the sibling that triggers this module's registrations."""

    @classmethod
    @register_method(
        name="extra",
        namespace=NAMESPACE,
        component="tests.fixtures.EmptyComponent",
    )
    def default(cls: Type[C]) -> C:
        return super().default()


class OuterConfig:
    """A configuration nested inside another class is still found."""

    class InnerConfig(BaseConfig):
        @classmethod
        @register_method(
            name="inner",
            namespace=NAMESPACE,
            component="tests.fixtures.EmptyComponent",
        )
        def default(cls: Type[C]) -> C:
            return super().default()
