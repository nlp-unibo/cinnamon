from cinnamon.configuration import Configuration
from cinnamon.registry import Registry, register


@register
def register_configurations():
    Registry.register_configuration(config=Configuration(),
                                    name='test2',
                                    namespace='external')