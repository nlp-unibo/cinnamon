from cinnamon.component import Component
from cinnamon.configuration import Configuration
from cinnamon.registry import Registry, register


@register
def register_configurations():
    Registry.register_configuration(config_class=Configuration,
                                    component_class=Component,
                                    name='test2',
                                    namespace='external')