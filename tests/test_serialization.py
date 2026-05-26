from cinnamon.registry import Registry, RegistrationKey
from cinnamon.configuration import Configuration
from cinnamon.component import Component
from tests.fixtures import (
    reset_registry,
    BaseComponent
)
from pathlib import Path


def test_save_empty_registry(
        reset_registry
):
    tmp_path = Path('.', Registry._REGISTRY_FILENAME).resolve()
    Registry.save_registry(filepath=tmp_path)
    assert tmp_path.exists()
    tmp_path.unlink()


def test_load_empty_registry(
        reset_registry
):
    tmp_path = Path('.', Registry._REGISTRY_FILENAME).resolve()
    Registry.save_registry(filepath=tmp_path)
    Registry.load_registry(filepath=tmp_path)
    assert len(Registry._REGISTRY) == 0
    tmp_path.unlink()


def test_save_registry_with_empty_config(
        reset_registry
):
    tmp_path = Path('.', Registry._REGISTRY_FILENAME).resolve()
    Registry.register_configuration(config=Configuration.default(),
                                    name='config',
                                    namespace='testing',
                                    component_class=Component)
    Registry.save_registry(filepath=tmp_path)
    Registry.load_registry(filepath=tmp_path)
    assert len(Registry._REGISTRY) == 1
    tmp_path.unlink()


def test_save_registry_with_custom_config(
        reset_registry
):
    tmp_path = Path('.', Registry._REGISTRY_FILENAME).resolve()

    config = Configuration.default()
    config.add(name='x', value=1)
    config.add(name='y', value=True)
    Registry.register_configuration(config=config,
                                    name='config',
                                    namespace='testing',
                                    component_class=Component)
    Registry.save_registry(filepath=tmp_path)
    Registry.load_registry(filepath=tmp_path)
    assert len(Registry._REGISTRY) == 1

    retrieved = Registry.retrieve_configuration(name='config', namespace='testing')
    assert retrieved == config
    assert retrieved.x == 1
    assert retrieved.y is True

    tmp_path.unlink()


def test_save_registry_with_dependencies(
        reset_registry
):
    tmp_path = Path('.', Registry._REGISTRY_FILENAME).resolve()

    parent_config = Configuration.default()
    parent_config.add(name='x', value=1)
    parent_config.add(name='c1', value=RegistrationKey(name='child', namespace='testing'))
    Registry.register_configuration(config=parent_config,
                                    name='config',
                                    namespace='testing',
                                    component_class=Component)

    child_config = Configuration.default()
    child_config.add(name='z', value=[1, 2, 3])
    Registry.register_configuration(config=child_config,
                                    name='child',
                                    namespace='testing',
                                    component_class=Component)

    Registry.dag_resolution()
    Registry.save_registry(filepath=tmp_path)
    Registry.load_registry(filepath=tmp_path)
    assert len(Registry._REGISTRY) == 2

    retrieved = Registry.retrieve_configuration(name='config', namespace='testing')
    assert retrieved.x == 1
    assert retrieved.c1 == child_config

    tmp_path.unlink()


def test_save_registry_with_config_with_custom_classes(
        reset_registry
):
    tmp_path = Path('.', Registry._REGISTRY_FILENAME).resolve()

    config = Configuration.default()
    config.add(name='x', value=1)
    config.add(name='y', value=BaseComponent(x=5, y=2))
    Registry.register_configuration(config=config,
                                    name='config',
                                    namespace='testing',
                                    component_class=Component)
    Registry.save_registry(filepath=tmp_path)
    Registry.load_registry(filepath=tmp_path)
    assert len(Registry._REGISTRY) == 1

    retrieved = Registry.retrieve_configuration(name='config', namespace='testing')
    assert retrieved.x == 1
    assert retrieved.y.x == 5
    assert retrieved.y.y == 2

    tmp_path.unlink()