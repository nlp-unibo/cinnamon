from cinnamon.component import Component
from cinnamon.configuration import Configuration
from cinnamon.registry import Registry, register


@register
def register_configurations():
    Registry.register_configuration(config=Configuration.default(),
                                    component_class=Component,
                                    name='test',
                                    namespace='external')


def deprecated_configurations():
    Registry.register_configuration(config=Configuration.default(),
                                    name='test',
                                    namespace='deprecated')
