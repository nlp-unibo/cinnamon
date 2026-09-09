"""A repo whose key points into a namespace registered by class decorator."""

from cinnamon.configuration import Configuration, Param
from cinnamon.registry import RegistrationKey, register_class


@register_class(
    name="config",
    namespace="consumer",
    component="tests.fixtures.EmptyComponent",
)
class ConsumerConfig(Configuration):
    child: RegistrationKey = Param(RegistrationKey(name="base", namespace="decorated"))
