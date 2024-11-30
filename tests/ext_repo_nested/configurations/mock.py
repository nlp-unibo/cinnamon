from cinnamon.registry import Registry, register, RegistrationKey
from cinnamon.configuration import Configuration, C
from typing import Type


class CustomConfiguration(Configuration):

    @classmethod
    def default(
            cls: Type[C]
    ) -> C:
        config = super().default()
        config.add(name='child', value=RegistrationKey(name='test', namespace='dep'))
        return config


@register
def register_configurations():
    Registry.register_configuration(config_class=CustomConfiguration,
                                    name='test',
                                    namespace='mock')
