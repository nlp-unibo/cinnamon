from typing import Type

from cinnamon.configuration import C, Configuration
from cinnamon.registry import RegistrationKey, register_method


class CustomConfiguration(Configuration):
    child: RegistrationKey = RegistrationKey(name="child", namespace="dep")

    @classmethod
    @register_method(name="test", namespace="mock")
    def default(cls: Type[C]) -> C:
        return cls()
