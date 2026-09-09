"""A repo that registers only through ``register_class``.

Nothing here declares a ``default`` it does not need, which is the point of the
decorator: the namespace has to be discoverable, and every configuration has to
build, without a single passthrough method in the directory.
"""

from cinnamon.configuration import Configuration, Param
from cinnamon.registry import register_class
from tests.class_repo.configurations.keys import NAMESPACE


@register_class(
    name="base",
    namespace=NAMESPACE,
    component="tests.fixtures.EmptyComponent",
)
class BaseConfig(Configuration):
    """No ``default`` of its own: it inherits the one every configuration has."""

    size: int = Param(1)


@register_class(
    name="derived",
    namespace=NAMESPACE,
    tags={"big"},
    component="tests.fixtures.EmptyComponent",
)
class DerivedConfig(BaseConfig):
    """Overrides a parameter and nothing else, which is the common case."""

    size: int = Param(2)


@register_class(
    name="conditioned",
    namespace=NAMESPACE,
    component="tests.fixtures.EmptyComponent",
)
class ConditionedConfig(BaseConfig):
    """Writes its own ``default``, and that is the one the registration builds."""

    @classmethod
    def default(cls):
        config = super().default()
        config.size = 3
        return config


class OuterConfig:
    """A configuration nested inside another class registers the same way."""

    @register_class(
        name="inner",
        namespace=NAMESPACE,
        component="tests.fixtures.EmptyComponent",
    )
    class InnerConfig(BaseConfig):
        size: int = Param(4)
