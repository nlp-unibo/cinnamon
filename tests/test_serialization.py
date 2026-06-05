from cinnamon.registry import Registry, RegistrationKey
from cinnamon.configuration import Configuration
from cinnamon.component import Component
from tests.fixtures import (
    reset_registry,
    BaseComponent,
    BaseConfig
)
from pathlib import Path


def test_save_empty_registry(
        reset_registry
):
    tmp_path = Path('.').resolve()

    Registry.save_registry(directory=tmp_path)

    assert tmp_path.exists()

    tmp_path.joinpath(Registry._REGISTRY_FILENAME).unlink()


def test_load_empty_registry(
        reset_registry
):
    tmp_path = Path('.').resolve()

    Registry.save_registry(directory=tmp_path)
    Registry.load_registry(directory=tmp_path)

    assert len(Registry._REGISTRY) == 0

    tmp_path.joinpath(Registry._REGISTRY_FILENAME).unlink()


def test_save_registry_with_empty_config(
        reset_registry
):
    tmp_path = Path('.').resolve()

    Registry.register_configuration(config=Configuration.default(),
                                    name='config',
                                    namespace='testing',
                                    component_class=Component)

    Registry.save_registry(directory=tmp_path)
    Registry.load_registry(directory=tmp_path)

    assert len(Registry._REGISTRY) == 1

    tmp_path.joinpath(Registry._REGISTRY_FILENAME).unlink()


def test_save_registry_with_custom_config(
        reset_registry
):
    tmp_path = Path('.').resolve()

    config = Configuration.default()
    config.add(name='x', value=1)
    config.add(name='y', value=True)

    Registry.register_configuration(config=config,
                                    name='config',
                                    namespace='testing',
                                    component_class=Component)

    Registry.save_registry(directory=tmp_path)
    Registry.load_registry(directory=tmp_path)
    assert len(Registry._REGISTRY) == 1

    retrieved = Registry.retrieve_configuration(name='config', namespace='testing')
    assert retrieved == config
    assert retrieved.x == 1
    assert retrieved.y is True

    tmp_path.joinpath(Registry._REGISTRY_FILENAME).unlink()


def test_save_registry_with_dependencies(
        reset_registry
):
    tmp_path = Path('.').resolve()

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
    Registry.save_registry(directory=tmp_path)
    Registry.load_registry(directory=tmp_path)
    assert len(Registry._REGISTRY) == 2

    retrieved = Registry.retrieve_configuration(name='config', namespace='testing')
    assert retrieved.x == 1
    assert retrieved.c1 == child_config

    tmp_path.joinpath(Registry._REGISTRY_FILENAME).unlink()


def test_save_registry_with_config_with_custom_classes(
        reset_registry
):
    tmp_path = Path('.').resolve()

    config = Configuration.default()
    config.add(name='x', value=1)
    config.add(name='y', value=BaseComponent(x=5, y=2))
    Registry.register_configuration(config=config,
                                    name='config',
                                    namespace='testing',
                                    component_class=Component)
    Registry.save_registry(directory=tmp_path)
    Registry.load_registry(directory=tmp_path)
    assert len(Registry._REGISTRY) == 1

    retrieved = Registry.retrieve_configuration(name='config', namespace='testing')
    assert retrieved.x == 1
    assert retrieved.y.x == 5
    assert retrieved.y.y == 2

    tmp_path.joinpath(Registry._REGISTRY_FILENAME).unlink()


def test_save_registry_with_articulated_custom_config(
        reset_registry
):
    tmp_path = Path('.').resolve()

    config = Configuration.default()
    config.add(name='pretrained_model_name', value='nlpaueb/legal-bert-base-uncased')
    config.add(name='data_dir', value=Path(__file__).parent.parent.resolve().joinpath('data'))
    config.add(name='category', value=None, variants=['A', 'CH', 'CR', 'LTD', 'TER'])
    config.add(name='tokenization_args', value={})
    config.add(name='batch_size', value=32)

    Registry.register_configuration(config=config,
                                    name='config',
                                    namespace='testing')
    Registry.save_registry(directory=tmp_path)
    Registry.load_registry(directory=tmp_path)

    retrieved = Registry.retrieve_configuration(name='config', namespace='testing')
    assert retrieved.pretrained_model_name == 'nlpaueb/legal-bert-base-uncased'
    assert retrieved.data_dir == Path(__file__).parent.parent.resolve().joinpath('data')
    assert retrieved.category is None
    assert retrieved.get('category').variants == ['A', 'CH', 'CR', 'LTD', 'TER']
    assert retrieved.tokenization_args == {}
    assert retrieved.batch_size == 32

    tmp_path.joinpath(Registry._REGISTRY_FILENAME).unlink()


def test_save_registry_with_external_config(
        reset_registry
):
    tmp_path = Path('.').resolve()

    directory = Path('.', 'tests', 'ext_repo_nested_dec')
    Registry.load_registrations(directory=directory)

    Registry.save_registry(directory=tmp_path)
    Registry.load_registry(directory=tmp_path)

    Registry.retrieve_configuration(name='config', tags={'nest1'}, namespace='testing')

    tmp_path.joinpath(Registry._REGISTRY_FILENAME).unlink()


# Test building component of loaded registry -> we might need to store DAG and other stuff
def test_save_registry_build_component(
        reset_registry
):
    tmp_path = Path('.').resolve()

    key = Registry.register_configuration(config=BaseConfig.default(),
                                          name='config',
                                          namespace='testing',
                                          component_class=BaseComponent)

    Registry.save_registry(directory=tmp_path)
    Registry.load_registry(directory=tmp_path)

    BaseComponent.build_component(registration_key=key)

    tmp_path.joinpath(Registry._REGISTRY_FILENAME).unlink()
