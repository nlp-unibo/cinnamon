from cinnamon.registry import Registry, register
from cinnamon.configuration import Configuration


@register
def register_configurations():
    Registry.register_configuration(config_class=Configuration,
                                    name='test',
                                    namespace='dep')
