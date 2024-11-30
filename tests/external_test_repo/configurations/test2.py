from cinnamon_core.component import Component
from cinnamon_core.configuration import Configuration
from cinnamon_core.registry import Registry, register


@register
def register_configurations():
    Registry.register_configuration(config_class=Configuration,
                                    component_class=Component,
                                    name='test2',
                                    namespace='external')