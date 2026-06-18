from cinnamon.configuration import Configuration
from cinnamon.registry import Registry, register


@register
def register_configurations():
    Registry.register_configuration(config=Configuration.default(),
                                    name='test',
                                    namespace='external',
                                    component='cinnamon.Component')


def deprecated_configurations():
    Registry.register_configuration(config=Configuration.default(),
                                    name='test',
                                    namespace='deprecated')
