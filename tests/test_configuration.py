from typing import Callable

import pydantic
import pytest

from cinnamon.configuration import Configuration, Param, ParamMeta
from cinnamon.registry import RegistrationKey, Registry
from cinnamon.utility.exceptions import ValidationFailureException
from tests.fixtures import (
    BaseConfig,
    ConfigWithMultipleVariants,
    ConfigWithVariants,
    InvalidConfig,
    NestedConfig,
    reset_registry,
)


def test_empty_configuration():
    """Test test empty configuration."""
    config = Configuration.default()
    assert len(config._conditions) == 0
    assert len(config.dependencies) == 0


def test_one_field_configuration():
    """Test test one field configuration."""
    config = BaseConfig.default()
    assert config.x == 5
    assert config.y == 10


def test_invalid_configuration():
    """Test test invalid configuration."""
    with pytest.raises(pydantic.ValidationError):
        InvalidConfig.default()


def test_add_condition():
    """
    Add condition to configuration and validate it,
    both with valid and invalid parameter values.
    """
    config = BaseConfig.default()
    config.add_condition(name="x_y_pairing", condition=lambda c: c.x == c.y / 2)
    config.validate_conditions()

    with pytest.raises(ValidationFailureException):
        copy_config = config.model_copy(update={"x": 10})
        copy_config.validate_conditions()


def test_add_existing_condition():
    """Test test add existing condition."""
    config = BaseConfig.default()
    config.add_condition(name="x_y_pairing", condition=lambda c: c.x == c.y / 2)

    with pytest.warns(RuntimeWarning):
        config.add_condition(name="x_y_pairing", condition=lambda c: c.x == c.y / 2)


def test_add_condition_conflicting_name():
    """Test test add condition conflicting name."""
    config = BaseConfig.default()
    config.add_condition(name="x", condition=lambda c: c.x > 1)


def test_validate_empty():
    """
    Validate empty configuration successfully
    """
    config = Configuration.default()
    result = config.validate_conditions()
    assert result.passed is True


def test_variants():
    """Test test variants."""
    config = ConfigWithMultipleVariants.default()

    v_combinations = config.variants
    assert len(v_combinations) == 8
    for comb in v_combinations:
        alt_config = config.model_copy(update=comb["values"])
        for key, value in comb["values"].items():
            assert getattr(alt_config, key) == value


def test_copy_with_custom_condition():
    """Test test copy with custom condition."""
    config = Configuration.default()
    config.add_condition(name="test-condition", condition=lambda c: True)
    assert "test-condition" in config._conditions
    assert config._conditions["test-condition"].condition(config) is True
    assert isinstance(config._conditions["test-condition"].condition, Callable)

    copy_config = config.model_copy(deep=True)
    assert "test-condition" in copy_config._conditions
    assert copy_config._conditions["test-condition"].condition(copy_config) is True
    assert isinstance(copy_config._conditions["test-condition"].condition, Callable)


def test_get_delta_copy_built():
    """
    Testing configuration.get_delta_copy()
    """
    config = BaseConfig.default()
    copy_config = config.model_copy(update={"x": 10})
    assert copy_config.x == 10
    copy_config.x = 20
    assert config.x == 5
    assert copy_config.x == 20


def test_get_delta_copy_built_nested():
    """
    Delta copy is not meant for hierarchy propagation
    """
    config = NestedConfig.default()
    copy_config = config.model_copy(deep=True)
    assert config.x == 10
    assert copy_config.x == 10
    assert id(config.child) != id(copy_config.child)

    copy_config.x = 5
    assert config.x == 10
    assert copy_config.x == 5

    copy_config.child.y = 20
    assert config.child.y == 10
    assert copy_config.child.y == 20


def test_to_value_dict():
    """Test test to value dict."""
    config = BaseConfig.default()
    value_dict = config.model_dump()
    assert value_dict == {"x": 5, "y": 10}


def test_nested_to_value_dict():
    """Test test nested to value dict."""
    config = NestedConfig.default()
    value_dict = config.model_dump()
    assert value_dict == {"x": 10, "child": {"x": 5, "y": 10}}


def test_validate_nested_config():
    """Test test validate nested config."""
    parent = NestedConfig.default()
    parent.add_condition(name="check_x", condition=lambda c: c.x > 0)
    parent.child.add_condition(name="check_x", condition=lambda c: c.x > 3)

    parent.validate_conditions()

    parent.child.x = 1
    with pytest.raises(ValidationFailureException):
        parent.child.validate_conditions(strict=True)

    with pytest.raises(ValidationFailureException):
        parent.validate_conditions(strict=True)


def test_configuration_variant_keys():
    """Test test configuration variant keys."""
    config = ConfigWithVariants.default()
    key = RegistrationKey(name="config", namespace="testing")

    for variant_info in config.variants:
        variant_key = key.from_variant(
            variant_kwargs=variant_info["values"],
            variant_indexes=variant_info["indexes"],
        )
        assert f"y{key.KEY_VALUE_SEPARATOR}5" not in variant_key.tags
        assert len(variant_key.tags) == 1
        assert variant_key.tags == {
            f"x{key.KEY_VALUE_SEPARATOR}{variant_info['values']['x']}"
        }


def test_configuration_with_multiple_variant_keys():
    """Test test configuration with multiple variant keys."""
    config = ConfigWithMultipleVariants.default()
    key = RegistrationKey(name="config", namespace="testing")

    for variant_info in config.variants:
        variant_key = key.from_variant(
            variant_kwargs=variant_info["values"],
            variant_indexes=variant_info["indexes"],
        )
        if variant_info["indexes"]["x"] != 0:
            assert (
                f"x{key.KEY_VALUE_SEPARATOR}{variant_info['values']['x']}"
                in variant_key.tags
            )
        if variant_info["indexes"]["y"] != 0:
            assert (
                f"y{key.KEY_VALUE_SEPARATOR}{variant_info['values']['y']}"
                in variant_key.tags
            )


# -- has_at_least_two_variants --


def test_has_at_least_two_variants_two_fields():
    """Test test has at least two variants two fields."""
    config = ConfigWithMultipleVariants.default()
    assert config.has_at_least_two_variants is True


def test_has_at_least_two_variants_single_field():
    """Test test has at least two variants single field."""
    config = ConfigWithVariants.default()
    assert config.has_at_least_two_variants is False


# -- FieldMetaProxy error paths --


def test_meta_bracket_missing_field_raises():
    """Test test meta bracket missing field raises."""
    config = BaseConfig.default()
    with pytest.raises(KeyError):
        config.meta["nope"]


def test_meta_attribute_missing_field_raises():
    """Test test meta attribute missing field raises."""
    config = BaseConfig.default()
    with pytest.raises(AttributeError):
        config.meta.nope


# -- MetaDescriptor class-level access --


def test_meta_class_context_variants():
    """Test test meta class context variants."""
    # Class context (instance is None): owner.model_fields is used.
    assert ConfigWithVariants.meta.x.variants == [2, 3]


def test_meta_class_context_missing_field_raises():
    """Test test meta class context missing field raises."""
    with pytest.raises(AttributeError):
        ConfigWithVariants.meta.nope


# -- Configuration.retrieve type mismatch --


def test_retrieve_type_mismatch_raises(reset_registry):
    """
    Retrieve a config whose registered type is not an instance of the
     requesting Configuration subclass.
    """
    Registry.register_configuration(
        config=Configuration.default(), name="x", namespace="testing"
    )
    with pytest.raises(RuntimeError):
        BaseConfig.retrieve(name="x", namespace="testing")


# -- validate_variants: default value also in variants --


def test_validate_variants_default_in_variants_raises():
    """
    A default value that is also listed in its own ``variants`` is rejected.
    """

    class BadVariantConfig(Configuration):
        x: int = Param(5, variants=[5, 6])

    with pytest.raises(ValueError):
        BadVariantConfig.default()


def test_validate_variants_required_field_skipped():
    """
    A required (no-default) field with variants is not checked against the
     default value: the ``PydanticUndefined`` branch short-circuits cleanly.
    """

    class RequiredVariantConfig(Configuration):
        x: int = Param(variants=[1, 2])

    config = RequiredVariantConfig(x=1)
    assert config.x == 1


# -- validate_conditions nested early-return with strict=False --


def test_validate_nested_failure_returns_child_result(reset_registry):
    """
    When a child dependency fails and ``strict=False``, the result of the
    failing child is returned early (the parent's own conditions are not
    evaluated).
    """
    parent = NestedConfig.default()
    parent.child.add_condition(
        name="child_fail", condition=lambda c: c.x > 100
    )
    parent.add_condition(name="parent_fail", condition=lambda c: c.y > 100)

    result = parent.validate_conditions(strict=False)
    assert result.passed is False
    assert result.source == "BaseConfig"  # child failing first, early-return


# -- ParamMeta / FieldMetaProxy leftovers --


def test_param_meta_call_no_op():
    """ParamMeta.__call__(schema) is a no-op and must not raise."""
    ParamMeta(tags=set(), variants=[]).__call__({})


def test_meta_class_context_none_schema_extra():
    """
    Class-context meta access on a field whose json_schema_extra is None
     lazily materializes a ParamMeta.
    """
    BaseConfig.model_fields["x"].json_schema_extra = None
    meta = BaseConfig.meta.x
    assert meta.variants == []
    assert BaseConfig.model_fields["x"].json_schema_extra is not None
