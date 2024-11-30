from cinnamon.registry import Registry, register
from tests.fixtures import ConfigWithExternalDependency, ComponentWithChild


@register
def register_configs():
    Registry.register_configuration(config_class=ConfigWithExternalDependency,
                                    component_class=ComponentWithChild,
                                    name='config',
                                    namespace='testing')
