from cinnamon.registry import Registry, register
from tests.fixtures import ConfigWithExternalDependency


@register
def register_configs():
    Registry.register_configuration(config=ConfigWithExternalDependency.default(),
                                    component='tests.fixtures.ComponentWithChild',
                                    name='config',
                                    namespace='testing')
