"""A repo that registers through keys declared in ``keys.py``.

No registration here names its namespace, so the scan finds it only by
following each ``key=`` back to ``Namespace("keyed")``.
"""

from cinnamon.configuration import Configuration, Param
from cinnamon.registry import (
    RegistrationKey,
    Registry,
    register,
    register_class,
    register_method,
)
from tests.key_repo.configurations.keys import BASE, CALLED, DERIVED, METHOD


@register_class(key=BASE, component="tests.fixtures.EmptyComponent", run_method="run")
class BaseConfig(Configuration):
    size: int = Param(1)


@register_class(key=DERIVED, component="tests.fixtures.EmptyComponent")
class DerivedConfig(BaseConfig):
    size: int = Param(2)
    child: RegistrationKey = Param(BASE)


class MethodConfig(BaseConfig):
    @classmethod
    @register_method(key=METHOD, component="tests.fixtures.EmptyComponent")
    def default(cls):
        config = super().default()
        config.size = 3
        return config


@register
def registrations():
    Registry.register_configuration(
        config=BaseConfig(size=4),
        key=CALLED,
        component="tests.fixtures.EmptyComponent",
    )
