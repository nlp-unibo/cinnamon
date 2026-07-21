import pytest

from cinnamon.configuration import Configuration
from cinnamon.registry import (
    RegistrationKey,
    Registry,
)
from cinnamon.utility.exceptions import (
    AlreadyRegisteredException,
    NotADAGException,
    NotRegisteredException,
)
from tests.fixtures import (
    BaseConfig,
    ChildConfig,
    CliqueConfigA,
    CliqueConfigB,
    ConfigWithChild,
    ConfigWithVariants,
    IntermediateWithChild,
    InvalidVariantConfig,
    LeafWithVariants,
    ParentWithVariantsAndChild,
    VariantConfigWithChild,
    VariantConfigWithVariantChild,
    expand_registry,
    reset_registry,
)

# Basic Registrations


def test_register_empty_config(reset_registry):
    """
    Register empty configuration and check if it is successful and
     if dependencies are correct
    """
    key = Registry.register_configuration(
        config=Configuration.default(), name="test", namespace="testing"
    )
    assert Registry.in_registry(key)
    assert key in Registry._DEPENDENCY_DAG

    assert len(Registry._DEPENDENCY_DAG.nodes) == 2
    assert len(Registry._DEPENDENCY_DAG.edges) == 1


def test_register_two_empty_configs(reset_registry):
    """
    Register two empty registrations and check corresponding dependencies
    """
    key_1 = Registry.register_configuration(
        config=Configuration.default(), name="test", namespace="testing"
    )
    key_2 = Registry.register_configuration(
        config=Configuration.default(), name="test", tags={"t2"}, namespace="testing"
    )
    assert Registry.in_registry(key_1)
    assert Registry.in_registry(key_2)

    assert len(Registry._DEPENDENCY_DAG.nodes) == 3
    assert len(Registry._DEPENDENCY_DAG.edges) == 2


def test_register_empty_and_nested_config(reset_registry):
    """
    Register two configurations, one with child, and check dependencies
    """

    key_1 = Registry.register_configuration(
        config=ConfigWithChild.default(), name="test", namespace="testing"
    )
    key_2 = Registry.register_configuration(
        config=Configuration.default(), name="test", tags={"t2"}, namespace="testing"
    )

    assert Registry.in_registry(key_1)
    assert Registry.in_registry(key_2)

    assert len(Registry._DEPENDENCY_DAG.nodes) == 3
    assert len(Registry._DEPENDENCY_DAG.edges) == 2
    assert (Registry._ROOT_KEY, key_1) in Registry._DEPENDENCY_DAG.edges
    assert (key_1, key_2) in Registry._DEPENDENCY_DAG.edges


def test_trigger_repeated_registration_error(reset_registry):
    """
    Register configuration and attempt registering it again to trigger error
    """

    Registry.register_configuration(
        config=Configuration.default(), name="test", tags={"tag1"}, namespace="testing"
    )
    with pytest.raises(AlreadyRegisteredException):
        Registry.register_configuration(
            config=Configuration.default(),
            name="test",
            tags={"tag1"},
            namespace="testing",
        )


def test_trigger_unregistered_config_error(reset_registry, expand_registry):
    """
    Trigger not registered exception when attempting to retrieve an unregistered config
    """

    registration_key = RegistrationKey(
        name="test_config", tags={"tag1", "tag2"}, namespace="testing"
    )

    with pytest.raises(NotRegisteredException):
        Registry.retrieve_configuration(registration_key=registration_key)


def test_retrieve_config(
    reset_registry,
):
    """
    Register and retrieve configuration with success
    """

    key = Registry.register_configuration(
        config=Configuration.default(), name="test_config", namespace="testing"
    )

    assert Registry.in_registry(key)
    Registry.retrieve_configuration(registration_key=key)


def test_register_and_bind_config(reset_registry):
    """
    Register a configuration with bounded component
    """
    key = Registry.register_configuration(
        config=Configuration.default(),
        component="cinnamon.component.Component",
        name="test",
        tags={"tag"},
        namespace="testing",
    )
    info = Registry.retrieve_configuration_info(key)
    assert "tag" in key.tags
    assert info.component is not None


def test_trigger_registered_config_with_binding_error(reset_registry):
    """
    Trigger exception when registering an already registered config
    with bounded component
    """

    Registry.register_configuration(
        config=Configuration.default(), name="test", tags={"tag"}, namespace="testing"
    )
    with pytest.raises(AlreadyRegisteredException):
        Registry.register_configuration(
            config=Configuration.default(),
            name="test",
            tags={"tag"},
            namespace="testing",
        )


def test_register_config_with_variants_no_expansion(reset_registry):
    """
    Register configuration with parameter variants and check newly created
     variants in dependency DAG
    """
    key = Registry.register_configuration(
        config=ConfigWithVariants.default(), name="test", namespace="testing"
    )
    assert Registry.in_registry(key)
    assert len(Registry._DEPENDENCY_DAG.nodes) == 2
    assert len(Registry._DEPENDENCY_DAG.edges) == 1
    assert (Registry._ROOT_KEY, key) in Registry._DEPENDENCY_DAG.edges
    assert (key, key.from_variant({"x": 1})) not in Registry._DEPENDENCY_DAG.edges
    assert (key, key.from_variant({"x": 2})) not in Registry._DEPENDENCY_DAG.edges
    assert (key, key.from_variant({"x": 3})) not in Registry._DEPENDENCY_DAG.edges


def test_register_config_with_child_and_variants_no_expansion(reset_registry):
    """
    Register configuration with child and parameter variants and check newly
     created variants in dependency DAG
    """

    key = Registry.register_configuration(
        config=VariantConfigWithChild.default(), name="test", namespace="testing"
    )
    assert Registry.in_registry(key)
    assert len(Registry._DEPENDENCY_DAG.nodes) == 3
    assert len(Registry._DEPENDENCY_DAG.edges) == 2
    assert (Registry._ROOT_KEY, key) in Registry._DEPENDENCY_DAG.edges
    assert (key, key.from_variant({"x": 1})) not in Registry._DEPENDENCY_DAG.edges
    assert (key, key.from_variant({"x": 2})) not in Registry._DEPENDENCY_DAG.edges
    assert (key, key.from_variant({"x": 3})) not in Registry._DEPENDENCY_DAG.edges

    child_key = Registry.register_configuration(
        config=Configuration.default(), name="test", tags={"t2"}, namespace="testing"
    )

    assert Registry.in_registry(child_key)
    assert len(Registry._DEPENDENCY_DAG.nodes) == 3
    assert len(Registry._DEPENDENCY_DAG.edges) == 2


def test_register_config_with_child_and_child_variants_no_expansion(reset_registry):
    """
    Register configuration with child variants and parameter variants and check
     newly created variants in dependency DAG
    """
    key = Registry.register_configuration(
        config=VariantConfigWithChild.default(), name="test", namespace="testing"
    )
    assert Registry.in_registry(key)
    assert len(Registry._DEPENDENCY_DAG.nodes) == 3
    assert len(Registry._DEPENDENCY_DAG.edges) == 2
    assert (Registry._ROOT_KEY, key) in Registry._DEPENDENCY_DAG.edges
    assert (key, key.from_variant({"x": 1})) not in Registry._DEPENDENCY_DAG.edges
    assert (key, key.from_variant({"x": 2})) not in Registry._DEPENDENCY_DAG.edges
    assert (key, key.from_variant({"x": 3})) not in Registry._DEPENDENCY_DAG.edges

    child_key = Registry.register_configuration(
        config=ChildConfig.default(), name="test", tags={"t2"}, namespace="testing"
    )

    assert Registry.in_registry(child_key)
    assert len(Registry._DEPENDENCY_DAG.nodes) == 3
    assert len(Registry._DEPENDENCY_DAG.edges) == 2

    assert (
        key.from_variant({"x": 1}),
        child_key.from_variant({"y": False}),
    ) not in Registry._DEPENDENCY_DAG.edges
    assert (
        key.from_variant({"x": 2}),
        child_key.from_variant({"y": False}),
    ) not in Registry._DEPENDENCY_DAG.edges
    assert (
        key.from_variant({"x": 3}),
        child_key.from_variant({"y": False}),
    ) not in Registry._DEPENDENCY_DAG.edges


def test_register_config_from_variant(reset_registry):
    """
    Testing registering a configuration delta copy (and building it)
    """

    config = BaseConfig.default()
    Registry.register_configuration(
        config=config.model_copy(update={"x": 10, "y": 15}),
        name="config",
        namespace="testing",
    )
    config: BaseConfig = Registry.retrieve_configuration(
        name="config", namespace="testing"
    )
    assert config.x == 10
    assert config.y == 15


#  Dependencies


def test_clique(reset_registry):
    """
    Testing that an exception occurs when the registration DAG contains
     a cycle (i.e., it is not a DAG)
    """

    Registry.register_configuration(
        config=CliqueConfigA.default(), name="config", tags={"c1"}, namespace="testing"
    )
    Registry.register_configuration(
        config=CliqueConfigB.default(), name="config", tags={"c2"}, namespace="testing"
    )
    with pytest.raises(NotADAGException):
        Registry.check_registration_graph()


def test_resolution_one_config_valid(reset_registry):
    """
    Registering a configuration with no parameters and check if resolutions
     returns that config key as valid
    """

    key = Registry.register_configuration(
        config=Configuration.default(), name="config", namespace="testing"
    )
    valid_keys, invalid_keys = Registry.dag_resolution()
    assert Registry.in_registry(key)
    assert key in valid_keys
    assert len(invalid_keys) == 0


def test_resolution_one_config_variants(reset_registry):
    """
    Registering a configuration with parameter variants and check
     if resolutions returns all keys as valid
    """
    key = Registry.register_configuration(
        config=ConfigWithVariants.default(), name="config", namespace="testing"
    )
    valid_keys, invalid_keys = Registry.dag_resolution()
    assert Registry.in_registry(key)
    assert key in valid_keys
    assert key.from_variant(variant_kwargs={"x": 2}) in valid_keys
    assert key.from_variant(variant_kwargs={"x": 3}) in valid_keys
    assert len(invalid_keys) == 0


def test_resolution_one_config_variants_some_invalid(reset_registry):
    """
    Registering a configuration with parameter variants and check if
     resolutions returns all keys as valid
    """
    key = Registry.register_configuration(
        config=InvalidVariantConfig.default(), name="config", namespace="testing"
    )
    valid_keys, invalid_keys = Registry.dag_resolution()
    assert Registry.in_registry(key)
    assert key in valid_keys
    assert key.from_variant(variant_kwargs={"x": 1}) in valid_keys
    assert key.from_variant(variant_kwargs={"x": 2}) in valid_keys
    assert key.from_variant(variant_kwargs={"x": 3}) in invalid_keys


def test_resolution_config_with_child_and_param_variants(reset_registry):
    """
    Registering a configuration with parameter variants and check if
     resolutions returns all keys as valid
    """
    parent_key = Registry.register_configuration(
        config=VariantConfigWithChild.default(), name="config", namespace="testing"
    )
    child_key = Registry.register_configuration(
        config=ChildConfig.default(), name="test", tags={"t2"}, namespace="testing"
    )
    valid_keys, invalid_keys = Registry.dag_resolution()
    assert len(valid_keys) == 8
    assert Registry.in_registry(parent_key)
    assert Registry.in_registry(child_key)
    assert parent_key in valid_keys
    assert (
        parent_key.from_variant(
            variant_kwargs={
                "x": 2,
                "c1": child_key.from_variant(variant_kwargs={"y": True}),
            }
        )
        in valid_keys
    )
    assert (
        parent_key.from_variant(
            variant_kwargs={
                "x": 3,
                "c1": child_key.from_variant(variant_kwargs={"y": True}),
            }
        )
        in valid_keys
    )
    assert parent_key.from_variant(variant_kwargs={"x": 2}) in valid_keys
    assert parent_key.from_variant(variant_kwargs={"x": 3}) in valid_keys
    assert (
        parent_key.from_variant(
            variant_kwargs={
                "c1": child_key.from_variant(variant_kwargs={"y": True}),
            }
        )
        in valid_keys
    )
    assert child_key in valid_keys
    assert child_key.from_variant(variant_kwargs={"y": True}) in valid_keys


def test_resolution_config_with_child_variants_pointing_to_variants(reset_registry):
    """
    We test the case where a config has a child with some variants,
     one of which points to another child.
    DAG resolution should consider all combinations
    """
    parent_key = Registry.register_configuration(
        config=ConfigWithChild.default(), name="config", namespace="testing"
    )
    first_child_key = Registry.register_configuration(
        config=VariantConfigWithVariantChild.default(),
        name="test",
        tags={"t2"},
        namespace="testing",
    )
    second_child_key = Registry.register_configuration(
        config=ConfigWithVariants.default(),
        name="test",
        tags={"t3"},
        namespace="testing",
    )
    valid_keys, invalid_keys = Registry.dag_resolution()
    assert Registry.in_registry(parent_key)
    assert Registry.in_registry(first_child_key)
    assert Registry.in_registry(second_child_key)
    assert len(valid_keys) == 15


def test_resolution_where_key_is_shared_in_more_than_one_path(reset_registry):
    Registry.register_configuration(
        config=ParentWithVariantsAndChild.default(),
        name="config",
        tags={"a"},
        namespace="testing",
    )
    Registry.register_configuration(
        config=ParentWithVariantsAndChild.default(),
        name="config",
        tags={"b"},
        namespace="testing",
    )
    Registry.register_configuration(
        config=Configuration.default(), name="intermediate", namespace="testing"
    )
    valid_keys, invalid_keys = Registry.dag_resolution()
    assert len(valid_keys) == 5
    assert len(invalid_keys) == 0


def test_resolution_where_key_with_variants_is_shared_in_more_than_one_path(
    reset_registry,
):
    Registry.register_configuration(
        config=ConfigWithChild.default(), name="config", tags={"a"}, namespace="testing"
    )
    Registry.register_configuration(
        config=ConfigWithChild.default(), name="config", tags={"b"}, namespace="testing"
    )
    Registry.register_configuration(
        config=ConfigWithVariants.default(),
        name="test",
        tags={"t2"},
        namespace="testing",
    )
    valid_keys, invalid_keys = Registry.dag_resolution()
    assert len(valid_keys) == 9
    assert len(invalid_keys) == 0


def test_hierarchy_with_conflicting_parameters(reset_registry):
    Registry.register_configuration(
        config=ParentWithVariantsAndChild.default(), name="parent", namespace="testing"
    )
    Registry.register_configuration(
        config=IntermediateWithChild.default(), name="intermediate", namespace="testing"
    )
    Registry.register_configuration(
        config=LeafWithVariants.default(), name="leaf", namespace="testing"
    )
    valid_keys, invalid_keys = Registry.dag_resolution()
    assert len(valid_keys) == 8


def test_hierarchy_with_conflicting_parameters_and_custom_constructor(reset_registry):
    Registry.register_configuration(
        config=ParentWithVariantsAndChild.default(), name="parent", namespace="testing"
    )
    Registry.register_configuration(
        config=IntermediateWithChild.custom_method(),
        name="intermediate",
        namespace="testing",
    )
    Registry.register_configuration(
        config=LeafWithVariants.default(), name="leaf", namespace="testing"
    )
    valid_keys, invalid_keys = Registry.dag_resolution()
    assert len(valid_keys) == 8

    parent = ParentWithVariantsAndChild.retrieve(name="parent", namespace="testing")
    parent.child = IntermediateWithChild.retrieve(name="intermediate", namespace="testing")
    assert parent.child.canarin == 10


def test_retrieve_keys(reset_registry):
    key = Registry.register_configuration(
        config=Configuration.default(), name="config", namespace="testing"
    )
    keys = Registry.retrieve_keys(names="config")
    assert len(keys) == 1
    assert keys == [key]


def test_retrieve_multiple_keys(reset_registry):
    a_key = Registry.register_configuration(
        config=Configuration.default(), name="config", namespace="testing"
    )
    b_key = Registry.register_configuration(
        config=Configuration.default(),
        name="config",
        tags={"another"},
        namespace="testing",
    )

    keys = Registry.retrieve_keys(names="config")
    assert len(keys) == 2
    assert a_key in keys
    assert b_key in keys

    keys = Registry.retrieve_keys(namespaces="testing")
    assert len(keys) == 2
    assert a_key in keys
    assert b_key in keys

    keys = Registry.retrieve_keys()
    assert len(keys) == 2
    assert a_key in keys
    assert b_key in keys

    keys = Registry.retrieve_keys(tags={"another"})
    assert len(keys) == 1
    assert a_key not in keys
    assert b_key in keys


def test_retrieve_keys_with_no_tags(reset_registry):
    key = Registry.register_configuration(
        config=Configuration.default(), name="config", namespace="testing"
    )

    keys = Registry.retrieve_keys(tags={None})
    assert len(keys) == 1
    assert key in keys


def test_retrieve_keys_with_all_conditions(reset_registry):
    key = Registry.register_configuration(
        config=Configuration.default(),
        name="config",
        tags={"a-tag"},
        namespace="testing",
    )
    other_key = Registry.register_configuration(
        config=Configuration.default(), name="other-config", namespace="other-testing"
    )
    keys = Registry.retrieve_keys(names="config", namespaces="testing")
    assert len(keys) == 1
    assert key in keys
    assert other_key not in keys


def test_dag_resolution(reset_registry):
    Registry.register_configuration(
        config=ParentWithVariantsAndChild.default(),
        name="config",
        namespace="testing",
    )
    Registry.register_configuration(
        config=Configuration.default(), name="intermediate", namespace="testing"
    )

    Registry.dag_resolution()

    retrieved = ParentWithVariantsAndChild.retrieve(name="config", namespace="testing")
    assert isinstance(retrieved.child, RegistrationKey)


def test_dag_resolution_with_variants(reset_registry):
    Registry.register_configuration(
        config=ParentWithVariantsAndChild.default(),
        name="config",
        namespace="testing"
    )
    Registry.register_configuration(
        config=Configuration.default(), name="intermediate", namespace="testing"
    )

    Registry.dag_resolution()

    retrieved = ParentWithVariantsAndChild.retrieve(name="config", namespace="testing")
    assert isinstance(retrieved.child, RegistrationKey)

    variant = ParentWithVariantsAndChild.retrieve(
        name="config", tags={"x=2"}, namespace="testing"
    )
    assert isinstance(variant.child, RegistrationKey)


def test_dag_resolution_with_invalid_variants(
    reset_registry,
):
    config = ParentWithVariantsAndChild.default()
    config.meta.x.variants = [2, 3]
    config.add_condition(name="invalidate_variant", condition=lambda c: c.x <= 2)

    Registry.register_configuration(
        config=config, name="config", namespace="testing"
    )
    Registry.register_configuration(
        config=LeafWithVariants.default(), name="intermediate", namespace="testing"
    )

    valid_keys, invalid_keys = Registry.dag_resolution()
    assert len(valid_keys) == 6

    retrieved = ParentWithVariantsAndChild.retrieve(name="config", namespace="testing")
    assert isinstance(retrieved.child, RegistrationKey)

    variant = ParentWithVariantsAndChild.retrieve(
        name="config", tags={"x=2"}, namespace="testing"
    )
    assert isinstance(variant.child, RegistrationKey)


def test_register_and_bind_runnable_component(reset_registry):
    key = Registry.register_configuration(
        config=Configuration.default(),
        name="test",
        tags={"tag"},
        namespace="testing",
        component="cinnamon.component.Component",
        run_method="__call__",
    )
    assert "tag" in key.tags
    assert "__runnable" in key.special_tags


def test_register_and_bind_custom_runnable_component(reset_registry):
    key = Registry.register_configuration(
        config=Configuration.default(),
        name="test",
        tags={"tag"},
        namespace="testing",
        component="tests.fixtures.CustomRunnableComponent",
        run_method="run",
    )
    assert "tag" in key.tags
    assert "__runnable" in key.special_tags


def test_retrieve_custom_runnable_component(reset_registry):
    key = Registry.register_configuration(
        config=Configuration.default(),
        name="test",
        tags={"tag"},
        namespace="testing",
        component="tests.fixtures.CustomRunnableComponent",
        run_method="run",
    )
    Registry.dag_resolution()

    config_info = Registry.retrieve_configuration_info(registration_key=key)
    component = Registry.instantiate(registration_key=key)

    assert config_info.run_method is not None
    assert hasattr(component, config_info.run_method)
    assert (
        getattr(component, config_info.run_method)()
        == "this is a mock runnable component"
    )


def test_retrieve_custom_runnable_component_with_variants(reset_registry):
    key = Registry.register_configuration(
        config=ConfigWithVariants.default(),
        name="test",
        tags={"tag"},
        namespace="testing",
        component="tests.fixtures.CustomRunnableComponentWithArgs",
        run_method="run",
    )
    Registry.dag_resolution()

    config_info = Registry.retrieve_configuration_info(registration_key=key)
    component = Registry.instantiate(registration_key=key)

    assert config_info.run_method is not None
    assert hasattr(component, config_info.run_method)
    assert getattr(component, config_info.run_method)() == 1

    variant_key = key.from_variant(variant_kwargs={"x": 2})
    variant_info = Registry.retrieve_configuration_info(registration_key=variant_key)
    variant_component = Registry.instantiate(registration_key=variant_key)

    assert variant_info.run_method is not None
    assert hasattr(variant_component, variant_info.run_method)
    assert getattr(variant_component, variant_info.run_method)() == 2
