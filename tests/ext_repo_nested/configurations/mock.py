from typing import Type

from cinnamon.configuration import Configuration, C
from cinnamon.registry import register_method, RegistrationKey


class CustomConfiguration(Configuration):

    @classmethod
    @register_method(name='test', namespace='mock')
    def default(
            cls: Type[C]
    ) -> C:
        config = super().default()
        config.add(name='child', value=RegistrationKey(name='test', namespace='dep'))
        return config
