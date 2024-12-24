import pytest

from cinnamon.component import Component
from cinnamon.configuration import Configuration
from cinnamon.registry import (
    Registry,
    RegistrationKey,
    NotRegisteredException,
    AlreadyRegisteredException,
    NotADAGException
)
from tests.fixtures import (
    reset_registry,
    expand_registry,
    ConfigWithChild,
    ConfigWithVariantChild,
    ChildConfig,
    VariantConfig,
    VariantConfigWithChild,
    VariantConfigWithVariantChild,
    BaseConfig,
    InvalidConfig,
    InvalidVariantConfig,
    CliqueConfigA,
    CliqueConfigB,
    ParentWithVariantsAndChild,
    IntermediateWithChild,
    LeafWithVariants
)


# Basic Registrations

def test_register_empty_config(
        reset_registry
):
    """
    Register empty configuration and check if it is successful and if dependencies are correct
    """
    key = Registry.register_configuration(config_class=Configuration,
                                          name='test',
                                          namespace='testing')
    assert Registry.in_registry(key)
    assert key in Registry._DEPENDENCY_DAG

    assert len(Registry._DEPENDENCY_DAG.nodes) == 2
    assert len(Registry._DEPENDENCY_DAG.edges) == 1


def test_register_two_empty_configs(
        reset_registry
):
    """
    Register two empty registrations and check corresponding dependencies
    """
    key_1 = Registry.register_configuration(config_class=Configuration,
                                            name='test',
                                            namespace='testing')
    key_2 = Registry.register_configuration(config_class=Configuration,
                                            name='test',
                                            tags={'t2'},
                                            namespace='testing')
    assert Registry.in_registry(key_1)
    assert Registry.in_registry(key_2)

    assert len(Registry._DEPENDENCY_DAG.nodes) == 3
    assert len(Registry._DEPENDENCY_DAG.edges) == 2


def test_register_empty_and_nested_config(
        reset_registry
):
    """
    Register two configurations, one with child, and check dependencies
    """

    key_1 = Registry.register_configuration(config_class=ConfigWithChild,
                                            name='test',
                                            namespace='testing')
    key_2 = Registry.register_configuration(config_class=Configuration,
                                            name='test',
                                            tags={'t2'},
                                            namespace='testing')

    assert Registry.in_registry(key_1)
    assert Registry.in_registry(key_2)

    assert len(Registry._DEPENDENCY_DAG.nodes) == 3
    assert len(Registry._DEPENDENCY_DAG.edges) == 2
    assert (Registry._ROOT_KEY, key_1) in Registry._DEPENDENCY_DAG.edges
    assert (key_1, key_2) in Registry._DEPENDENCY_DAG.edges


def test_trigger_repeated_registration_error(
        reset_registry
):
    """
    Register configuration and attempt registering it again to trigger error
    """

    Registry.register_configuration(config_class=Configuration,
                                    name='test',
                                    tags={'tag1'},
                                    namespace='testing')
    with pytest.raises(AlreadyRegisteredException):
        Registry.register_configuration(config_class=Configuration,
                                        name='test',
                                        tags={'tag1'},
                                        namespace='testing')


def test_trigger_unregistered_config_error(
        reset_registry,
        expand_registry
):
    """
    Trigger not registered exception when attempting to retrieve an unregistered config
    """

    registration_key = RegistrationKey(name='test_config',
                                       tags={'tag1', 'tag2'},
                                       namespace='testing')

    with pytest.raises(NotRegisteredException):
        Registry.retrieve_configuration(registration_key=registration_key)


def test_retrieve_config(
        reset_registry,
):
    """
    Register and retrieve configuration with success
    """

    key = Registry.register_configuration(config_class=Configuration,
                                          name='test_config',
                                          namespace='testing')

    assert Registry.in_registry(key)
    Registry.retrieve_configuration(registration_key=key)


def test_register_and_bind_config(
        reset_registry
):
    """
    Register a configuration with bounded component
    """
    key = Registry.register_configuration(config_class=Configuration,
                                          component_class=Component,
                                          name='test',
                                          tags={'tag'},
                                          namespace='testing')
    info = Registry.retrieve_configuration_info(key)
    assert info.component_class is not None


def test_trigger_registered_config_with_binding_error(
        reset_registry
):
    """
    Trigger exception when registering an already registered config with bounded component
    """

    Registry.register_configuration(config_class=Configuration,
                                    component_class=Component,
                                    name='test',
                                    tags={'tag'},
                                    namespace='testing')
    with pytest.raises(AlreadyRegisteredException):
        Registry.register_configuration(config_class=Configuration,
                                        component_class=Component,
                                        name='test',
                                        tags={'tag'},
                                        namespace='testing')


def test_register_config_with_variants_no_expansion(
        reset_registry
):
    """
    Register configuration with parameter variants and check newly created variants in dependency DAG
    """
    key = Registry.register_configuration(config_class=VariantConfig,
                                          name='test',
                                          namespace='testing')
    assert Registry.in_registry(key)
    assert len(Registry._DEPENDENCY_DAG.nodes) == 2
    assert len(Registry._DEPENDENCY_DAG.edges) == 1
    assert (Registry._ROOT_KEY, key) in Registry._DEPENDENCY_DAG.edges
    assert (key, key.from_variant({'x': 1})) not in Registry._DEPENDENCY_DAG.edges
    assert (key, key.from_variant({'x': 2})) not in Registry._DEPENDENCY_DAG.edges
    assert (key, key.from_variant({'x': 3})) not in Registry._DEPENDENCY_DAG.edges


def test_register_config_with_child_and_variants_no_expansion(
        reset_registry
):
    """
    Register configuration with child and parameter variants and check newly created variants in dependency DAG
    """

    # First avoid registering child key -- we should still see all connections
    key = Registry.register_configuration(config_class=VariantConfigWithChild,
                                          name='test',
                                          namespace='testing')
    assert Registry.in_registry(key)
    assert len(Registry._DEPENDENCY_DAG.nodes) == 3
    assert len(Registry._DEPENDENCY_DAG.edges) == 2
    assert (Registry._ROOT_KEY, key) in Registry._DEPENDENCY_DAG.edges
    assert (key, key.from_variant({'x': 1})) not in Registry._DEPENDENCY_DAG.edges
    assert (key, key.from_variant({'x': 2})) not in Registry._DEPENDENCY_DAG.edges
    assert (key, key.from_variant({'x': 3})) not in Registry._DEPENDENCY_DAG.edges

    # No additions should be made here
    child_key = Registry.register_configuration(config_class=Configuration,
                                                name='test',
                                                tags={'t2'},
                                                namespace='testing')

    assert Registry.in_registry(child_key)
    assert len(Registry._DEPENDENCY_DAG.nodes) == 3
    assert len(Registry._DEPENDENCY_DAG.edges) == 2


def test_register_config_with_child_and_child_variants_no_expansion(
        reset_registry
):
    """
    Register configuration with child variants and parameter variants and check newly created variants in dependency DAG
    """
    # First avoid registering child key -- we should still see all connections
    key = Registry.register_configuration(config_class=VariantConfigWithChild,
                                          name='test',
                                          namespace='testing')
    assert Registry.in_registry(key)
    assert len(Registry._DEPENDENCY_DAG.nodes) == 3
    assert len(Registry._DEPENDENCY_DAG.edges) == 2
    assert (Registry._ROOT_KEY, key) in Registry._DEPENDENCY_DAG.edges
    assert (key, key.from_variant({'x': 1})) not in Registry._DEPENDENCY_DAG.edges
    assert (key, key.from_variant({'x': 2})) not in Registry._DEPENDENCY_DAG.edges
    assert (key, key.from_variant({'x': 3})) not in Registry._DEPENDENCY_DAG.edges

    # Additions are made here since child has variants
    child_key = Registry.register_configuration(config_class=ChildConfig,
                                                name='test',
                                                tags={'t2'},
                                                namespace='testing')

    assert Registry.in_registry(child_key)
    assert len(Registry._DEPENDENCY_DAG.nodes) == 3
    assert len(Registry._DEPENDENCY_DAG.edges) == 2

    # Check edges that will be integrated during dag resolution
    assert (key.from_variant({'x': 1}), child_key.from_variant({'y': False})) not in Registry._DEPENDENCY_DAG.edges
    assert (key.from_variant({'x': 2}), child_key.from_variant({'y': False})) not in Registry._DEPENDENCY_DAG.edges
    assert (key.from_variant({'x': 3}), child_key.from_variant({'y': False})) not in Registry._DEPENDENCY_DAG.edges


def test_register_config_from_variant(
        reset_registry
):
    """
    Testing registering a configuration delta copy (and building it)
    """

    Registry.register_configuration_from_variant(config_class=BaseConfig,
                                                 component_class=Component,
                                                 name='config',
                                                 namespace='testing',
                                                 variant_kwargs={
                                                     'x': 10,
                                                     'y': 15
                                                 })
    config = Registry.retrieve_configuration(name='config',
                                             namespace='testing')
    assert config.x == 10
    assert config.y == 15


#  Dependencies

def test_clique(
        reset_registry
):
    """
    Testing that an exception occurs when the registration DAG contains a cycle (i.e., it is not a DAG)
    """

    Registry.register_configuration(config_class=CliqueConfigA,
                                    name='config',
                                    tags={'c1'},
                                    namespace='testing')
    Registry.register_configuration(config_class=CliqueConfigB,
                                    name='config',
                                    tags={'c2'},
                                    namespace='testing')
    with pytest.raises(NotADAGException):
        Registry.check_registration_graph()


def test_resolution_one_config_valid(
        reset_registry
):
    """
    Registering a configuration with no parameters and check if resolutions returns that config key as valid
    """

    key = Registry.register_configuration(config_class=Configuration,
                                          name='config',
                                          namespace='testing')
    valid_keys, invalid_keys = Registry.dag_resolution()
    assert Registry.in_registry(key)
    assert key in valid_keys
    assert len(invalid_keys) == 0


def test_resolution_one_config_invalid(
        reset_registry
):
    """
    Registering a configuration with an invalid parameter value
    and check if resolutions returns that config key as invalid
    """
    key = Registry.register_configuration(config_class=InvalidConfig,
                                          name='config',
                                          namespace='testing')
    valid_keys, invalid_keys = Registry.dag_resolution()
    assert Registry.in_registry(key)
    assert key not in valid_keys
    assert key in invalid_keys


def test_resolution_one_config_variants(
        reset_registry
):
    """
    Registering a configuration with parameter variants and check if resolutions returns all keys as valid
    """
    key = Registry.register_configuration(config_class=VariantConfig,
                                          name='config',
                                          namespace='testing')
    valid_keys, invalid_keys = Registry.dag_resolution()
    assert Registry.in_registry(key)
    assert key.from_variant(variant_kwargs={'x': 1}) in valid_keys
    assert key.from_variant(variant_kwargs={'x': 2}) in valid_keys
    assert key.from_variant(variant_kwargs={'x': 3}) in valid_keys
    assert key in invalid_keys


def test_resolution_one_config_variants_some_invalid(
        reset_registry
):
    """
    Registering a configuration with parameter variants and check if resolutions returns all keys as valid
    """
    key = Registry.register_configuration(config_class=InvalidVariantConfig,
                                          name='config',
                                          namespace='testing')
    valid_keys, invalid_keys = Registry.dag_resolution()
    assert Registry.in_registry(key)
    assert key in valid_keys
    assert key.from_variant(variant_kwargs={'x': 1}) in valid_keys
    assert key.from_variant(variant_kwargs={'x': 2}) in valid_keys
    assert key.from_variant(variant_kwargs={'x': 3}) in invalid_keys


def test_resolution_config_with_child_and_param_variants(
        reset_registry
):
    """
    Registering a configuration with parameter variants and check if resolutions returns all keys as valid
    """
    parent_key = Registry.register_configuration(config_class=VariantConfigWithChild,
                                                 name='config',
                                                 namespace='testing')
    child_key = Registry.register_configuration(config_class=ChildConfig,
                                                name='test',
                                                tags={'t2'},
                                                namespace='testing')
    valid_keys, invalid_keys = Registry.dag_resolution()
    assert len(valid_keys) == 8
    assert Registry.in_registry(parent_key)
    assert Registry.in_registry(child_key)
    assert parent_key in invalid_keys
    assert child_key in invalid_keys
    assert parent_key.from_variant(
        variant_kwargs={'x': 1, 'c1': child_key.from_variant(variant_kwargs={'y': False})}) in valid_keys
    assert parent_key.from_variant(
        variant_kwargs={'x': 1, 'c1': child_key.from_variant(variant_kwargs={'y': True})}) in valid_keys
    assert parent_key.from_variant(
        variant_kwargs={'x': 2, 'c1': child_key.from_variant(variant_kwargs={'y': False})}) in valid_keys
    assert parent_key.from_variant(
        variant_kwargs={'x': 2, 'c1': child_key.from_variant(variant_kwargs={'y': True})}) in valid_keys
    assert parent_key.from_variant(
        variant_kwargs={'x': 3, 'c1': child_key.from_variant(variant_kwargs={'y': False})}) in valid_keys
    assert parent_key.from_variant(
        variant_kwargs={'x': 3, 'c1': child_key.from_variant(variant_kwargs={'y': True})}) in valid_keys
    assert child_key.from_variant(variant_kwargs={'y': False}) in valid_keys
    assert child_key.from_variant(variant_kwargs={'y': True}) in valid_keys


def test_resolution_config_with_child_variants_pointing_to_variants(
        reset_registry
):
    """
    We test the case where a config has a child with some variants, one of which points to another child
    DAG resolution should consider all combinations
    """
    parent_key = Registry.register_configuration(config_class=ConfigWithChild,
                                                 name='config',
                                                 namespace='testing')
    first_child_key = Registry.register_configuration(config_class=VariantConfigWithVariantChild,
                                                      name='test',
                                                      tags={'t2'},
                                                      namespace='testing')
    second_child_key = Registry.register_configuration(config_class=VariantConfig,
                                                       name='test',
                                                       tags={'t3'},
                                                       namespace='testing')
    valid_keys, invalid_keys = Registry.dag_resolution()
    assert Registry.in_registry(parent_key)
    assert Registry.in_registry(first_child_key)
    assert Registry.in_registry(second_child_key)
    assert len(valid_keys) == 15


def test_resolution_config_with_variant_dependency(
        reset_registry
):
    """
    We test the case where a config has a child which is a variant of another config
    """
    variant_key = Registry.register_configuration(config_class=VariantConfig,
                                                  name='test',
                                                  namespace='testing')
    dep_key = Registry.register_configuration(config_class=ConfigWithVariantChild,
                                              name='config',
                                              namespace='testing')
    valid_keys, invalid_keys = Registry.dag_resolution()

    dep_config = Registry.build_configuration(name='config', namespace='testing')
    assert dep_config.c1.x == 1


def test_resolution_where_key_is_shared_in_more_than_one_path(
        reset_registry
):
    first_key = Registry.register_configuration(config_class=ParentWithVariantsAndChild,
                                                name='config',
                                                tags={'a'},
                                                namespace='testing')
    second_key = Registry.register_configuration(config_class=ParentWithVariantsAndChild,
                                                 name='config',
                                                 tags={'b'},
                                                 namespace='testing')
    shared_key = Registry.register_configuration(config_class=Configuration,
                                                 name='intermediate',
                                                 namespace='testing')
    valid_keys, invalid_keys = Registry.dag_resolution()
    assert len(valid_keys) == 5
    assert len(invalid_keys) == 2


def test_resolution_where_key_with_variants_is_shared_in_more_than_one_path(
        reset_registry
):
    first_key = Registry.register_configuration(config_class=ConfigWithChild,
                                                name='config',
                                                tags={'a'},
                                                namespace='testing')
    second_key = Registry.register_configuration(config_class=ConfigWithChild,
                                                 name='config',
                                                 tags={'b'},
                                                 namespace='testing')
    shared_key = Registry.register_configuration(config_class=VariantConfig,
                                                 name='test',
                                                 tags={'t2'},
                                                 namespace='testing')
    valid_keys, invalid_keys = Registry.dag_resolution()
    assert len(valid_keys) == 9
    assert len(invalid_keys) == 3


def test_hierarchy_with_conflicting_parameters(
        reset_registry
):
    Registry.register_configuration(config_class=ParentWithVariantsAndChild,
                                    name='parent',
                                    namespace='testing')
    Registry.register_configuration(config_class=IntermediateWithChild,
                                    name='intermediate',
                                    namespace='testing')
    Registry.register_configuration(config_class=LeafWithVariants,
                                    name='leaf',
                                    namespace='testing')
    valid_keys, invalid_keys = Registry.dag_resolution()
    assert len(valid_keys) == 8



