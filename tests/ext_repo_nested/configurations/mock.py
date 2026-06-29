from typing import Type

from cinnamon.configuration import C, Configuration
from cinnamon.registry import RegistrationKey, register_method


class CustomConfiguration(Configuration):
    @classmethod
    @register_method(name="test", namespace="mock")
    def default(cls: Type[C]) -> C:
        config = super().default()
        config.add(name="child", value=RegistrationKey(name="test", namespace="dep"))
        return config
