import pytest

from cinnamon_core.component import Component
from cinnamon_core.configuration import Configuration
from cinnamon_core.registry import Registry, RegistrationKey
from tests.fixtures import (
    reset_registry,
    BaseConfig,
    BaseComponent,
    ConfigWithChild,
    ChildConfig,
    ComponentWithChild,
    ChildComponent,
    ConfigWithExternalDependency
)
from pathlib import Path


def test_build_empty_component(
        reset_registry
):
    """
    Testing if we can build component from its configuration key
    """

    key = Registry.register_configuration(config_class=Configuration,
                                          component_class=Component,
                                          name='component',
                                          namespace='testing')
    Registry.expanded = True
    component = Registry.build_component(registration_key=key)
    assert type(component) == Component


def test_build_component(
        reset_registry
):
    """
    Build component via registered key and check parameters
    """
    key = Registry.register_configuration(config_class=BaseConfig,
                                          component_class=BaseComponent,
                                          name='component',
                                          namespace='testing')
    Registry.expanded = True
    component = BaseComponent.build_component(registration_key=key)
    assert type(component) == BaseComponent
    assert component.x == 5
    assert component.y == 10


def test_trigger_invalid_build_component(
        reset_registry
):
    """
    Trigger exception when building a component with an improper configuration
    """
    key = Registry.register_configuration(config_class=BaseConfig,
                                          component_class=Component,
                                          name='component',
                                          namespace='testing')
    Registry.expanded = True
    with pytest.raises(TypeError):
        Registry.build_component(registration_key=key)


def test_build_component_with_child(
        reset_registry
):
    """
    Build component that contains another child component
    """
    parent_key = Registry.register_configuration(config_class=ConfigWithChild,
                                                 component_class=ComponentWithChild,
                                                 name='config',
                                                 namespace='testing')
    child_key = Registry.register_configuration(config_class=ChildConfig,
                                                component_class=ChildComponent,
                                                name='test',
                                                tags={'t2'},
                                                namespace='testing')
    Registry.expanded = True
    parent_component = ComponentWithChild.build_component(registration_key=parent_key)
    child_component = ChildComponent.build_component(registration_key=child_key)

    assert isinstance(parent_component.c1, ChildComponent)
    assert parent_component.c1.y is None
    assert parent_component.c1 != child_component


def test_build_component_with_child_variants(
        reset_registry
):
    """
    Build component with child component and also build one of its variant
    """
    parent_key = Registry.register_configuration(config_class=ConfigWithChild,
                                                 component_class=ComponentWithChild,
                                                 name='config',
                                                 namespace='testing')
    child_key = Registry.register_configuration(config_class=ChildConfig,
                                                component_class=ChildComponent,
                                                name='test',
                                                tags={'t2'},
                                                namespace='testing')
    Registry.dag_resolution()
    parent_component = ComponentWithChild.build_component(registration_key=parent_key)
    child_component = ChildComponent.build_component(registration_key=child_key)

    assert isinstance(parent_component.c1, ChildComponent)
    assert parent_component.c1.y is None
    assert parent_component.c1 != child_component

    variant_parent_component = ComponentWithChild.build_component(
        registration_key=parent_key.from_variant({'c1': child_key.from_variant({'y': True})}))
    assert variant_parent_component.c1.y is True


def test_build_external_component(
        reset_registry
):
    """
    Testing Component building API for an external registration.
    """

    external_path = Path().parent.resolve().joinpath('external_test_repo')
    Registry.load_registrations(directory=external_path)
    Registry.dag_resolution()
    component = Registry.build_component(name='test',
                                         namespace='external')
    assert isinstance(component, Component)


def test_build_component_with_external_dependency(
        reset_registry
):
    external_path = Path().parent.resolve().joinpath('external_test_repo')

    namespaces, mapping = Registry.parse_configuration_files(directories=[external_path])
    Registry.update_namespaces(namespaces=namespaces, module_mapping=mapping)

    key = Registry.register_configuration(config_class=ConfigWithExternalDependency,
                                          component_class=ComponentWithChild,
                                          name='config',
                                          namespace='testing')
    Registry.dag_resolution()

    component = ComponentWithChild.build_component(registration_key=key)
    assert type(component.c1) == Component


def test_build_after_setup(
        reset_registry
):
    main_path = Path().parent.resolve().joinpath('fake_main')
    external_directories = [
        Path().parent.resolve().joinpath('external_test_repo')
    ]
    Registry.setup(directory=main_path,
                   external_directories=external_directories)
    key = RegistrationKey(name='config', namespace='testing')
    component = ComponentWithChild.build_component(registration_key=key)
    assert type(component.c1) == Component
