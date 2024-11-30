from cinnamon_core.registry import Registry, register
from cinnamon_core.configuration import Configuration


@register
def register_configurations():
    Registry.register_configuration(config_class=Configuration,
                                    name='test',
                                    namespace='dep')
