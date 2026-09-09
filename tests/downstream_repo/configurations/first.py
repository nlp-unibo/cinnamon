from cinnamon.configuration import Configuration, Param
from cinnamon.registry import RegistrationKey, register_method


class FirstConfig(Configuration):
    """Depends on another namespace, which is what loads that namespace."""

    child: RegistrationKey = Param(RegistrationKey(name="test", namespace="dep"))

    @classmethod
    @register_method(
        name="config",
        tags={"first"},
        namespace="downstream",
        component="tests.fixtures.EmptyComponent",
    )
    def default(cls):
        return super().default()
