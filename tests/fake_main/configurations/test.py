from cinnamon.registry import Registry, register
from tests.fixtures import ConfigWithExternalDependency


@register
def register_configs():
    Registry.register_configuration(config=ConfigWithExternalDependency.default(),
                                    name='config',
                                    namespace='testing')
