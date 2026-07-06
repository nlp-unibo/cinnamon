from typing import Callable

import pydantic
import pytest

from cinnamon.configuration import Configuration
from cinnamon.registry import RegistrationKey
from cinnamon.utility.exceptions import ValidationFailureException
from tests.fixtures import (
    BaseConfig,
    ConfigWithMultipleVariants,
    ConfigWithVariants,
    InvalidConfig,
    NestedConfig,
)


def test_empty_configuration():
    config = Configuration.default()
    assert len(config._conditions) == 0
    assert len(config.dependencies) == 0


def test_one_field_configuration():
    config = BaseConfig.default()
    assert config.x == 5
    assert config.y == 10


def test_invalid_configuration():
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


def test_add_condition_conflicting_name():
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
    config = ConfigWithMultipleVariants.default()

    v_combinations = config.variants
    assert len(v_combinations) == 8
    for comb in v_combinations:
        alt_config = config.model_copy(update=comb['values'])
        for key, value in comb['values'].items():
            assert getattr(alt_config, key) == value


def test_copy_with_custom_condition():
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
    config = BaseConfig.default()
    value_dict = config.model_dump()
    assert value_dict == {"x": 5, "y": 10}


def test_nested_to_value_dict():
    config = NestedConfig.default()
    value_dict = config.model_dump()
    assert value_dict == {"x": 10, "child": {"x": 5, "y": 10}}


def test_validate_nested_config():
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
    config = ConfigWithMultipleVariants.default()
    key = RegistrationKey(name="config", namespace="testing")

    for variant_info in config.variants:
        variant_key = key.from_variant(
            variant_kwargs=variant_info["values"],
            variant_indexes=variant_info["indexes"],
        )
        if variant_info['indexes']['x'] != 0:
            assert (
                f"x{key.KEY_VALUE_SEPARATOR}{variant_info['values']['x']}"
                in variant_key.tags
            )
        if variant_info['indexes']['y'] != 0:
            assert (
                f"y{key.KEY_VALUE_SEPARATOR}{variant_info['values']['y']}"
                in variant_key.tags
            )
