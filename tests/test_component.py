import pytest

from cinnamon.component import Component
from cinnamon.configuration import Configuration
from cinnamon.registry import Registry, RegistrationKey
from tests.fixtures import (
    reset_registry,
    BaseConfig,
    BaseComponent,
    ConfigWithChild,
    ChildConfig,
    ComponentWithChild,
    ConfigWithExternalDependency
)
from pathlib import Path


def test_build_empty_component(
        reset_registry
):
    """
    Testing if we can build component from its configuration key
    """

    key = Registry.register_configuration(config=Configuration.default(),
                                          component='cinnamon.component.Component',
                                          name='component',
                                          namespace='testing')
    Registry.expanded = True
    component = Registry.instantiate_component(registration_key=key)
    assert type(component) == Component


def test_build_component(
        reset_registry
):
    """
    Build component via registered key and check parameters
    """
    key = Registry.register_configuration(config=BaseConfig.default(),
                                          component='tests.fixtures.BaseComponent',
                                          name='component',
                                          namespace='testing')
    Registry.expanded = True

    component = BaseComponent.instantiate_component(registration_key=key)
    assert type(component) == BaseComponent
    assert component.x == 5
    assert component.y == 10

    component = Registry.instantiate_component(registration_key=key)
    assert type(component) == BaseComponent
    assert component.x == 5
    assert component.y == 10


def test_trigger_invalid_build_component(
        reset_registry
):
    """
    Trigger exception when building a component with an improper configuration
    """
    key = Registry.register_configuration(config=Configuration.default(),
                                          component='tests.fixtures.BaseComponent',
                                          name='component',
                                          namespace='testing')
    Registry.expanded = True
    with pytest.raises(TypeError):
        Registry.instantiate_component(registration_key=key)


def test_build_component_with_child(
        reset_registry
):
    """
    Build component that contains another child component
    """
    parent_key = Registry.register_configuration(config=ConfigWithChild.default(),
                                                 name='config',
                                                 namespace='testing')
    Registry.register_configuration(config=ChildConfig.default(),
                                                name='test',
                                                tags={'t2'},
                                                namespace='testing')
    Registry.dag_resolution()

    parent_component = ComponentWithChild.instantiate_component(registration_key=parent_key)

    assert isinstance(parent_component.c1, ChildConfig)
    assert parent_component.c1.y is None


def test_build_component_with_child_variants(
        reset_registry
):
    """
    Build component with child component and also build one of its variant
    """
    parent_key = Registry.register_configuration(config=ConfigWithChild.default(),
                                                 name='config',
                                                 namespace='testing')
    child_key = Registry.register_configuration(config=ChildConfig.default(),
                                                name='test',
                                                tags={'t2'},
                                                namespace='testing')
    Registry.dag_resolution()

    parent_component = ComponentWithChild.instantiate_component(registration_key=parent_key)
    assert isinstance(parent_component.c1, ChildConfig)
    assert parent_component.c1.y is None

    variant_parent_config = Registry.retrieve_configuration(registration_key=parent_key.from_variant({'c1': child_key.from_variant({'y': True})}))
    assert variant_parent_config.c1.y is True


def test_build_external_component(
        reset_registry
):
    """
    Testing Component building API for an external registration.
    """

    external_path = Path().parent.resolve().joinpath('tests', 'external_test_repo')
    Registry.load_registrations(directory=external_path)
    Registry.dag_resolution()

    config = Registry.retrieve_configuration(name='test', namespace='external')
    assert isinstance(config, Configuration)


def test_build_component_with_external_dependency(
        reset_registry
):
    external_path = Path().parent.resolve().joinpath('tests', 'external_test_repo')

    namespaces, mapping = Registry.parse_configuration_files(directories=[external_path])
    Registry.update_namespaces(namespaces=namespaces, module_mapping=mapping)

    key = Registry.register_configuration(config=ConfigWithExternalDependency.default(),
                                          name='config',
                                          namespace='testing')
    Registry.dag_resolution()

    component = ComponentWithChild.instantiate_component(registration_key=key)
    assert type(component.c1) == Configuration


def test_build_after_setup(
        reset_registry
):
    main_path = Path().parent.resolve().joinpath('tests', 'fake_main')
    external_directories = [
        Path().parent.resolve().joinpath('tests', 'external_test_repo')
    ]
    Registry.build(directory=main_path,
                   external_directories=external_directories)
    key = RegistrationKey(name='config', namespace='testing')

    component = ComponentWithChild.instantiate_component(registration_key=key)
    assert type(component.c1) == Configuration
