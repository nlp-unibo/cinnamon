from copy import deepcopy
from email.policy import strict
from typing import List

import pytest

from cinnamon.registry import RegistrationKey
from cinnamon.configuration import Configuration, ValidationFailureException, Param
from tests.fixtures import define_configuration


def test_adding_param():
    """
    Add parameter to config and retrieve it
    """

    config = Configuration()
    config.add(name='x',
               value=50,
               type_hint=int,
               description="test description")
    assert config.x == 50
    assert config.get('x').value == 50
    assert type(config.get('x')) == Param


def test_init_from_kwargs():
    """
    Initialize configuration via __init__ and retrieve parameter
    """

    config = Configuration(x=50)
    assert config.x == 50
    assert config.get('x').value == 50
    assert type(config.get('x')) == Param


def test_trigger_typecheck_error():
    """
    Trigger typecheck error on invalid parameter value
    """

    config = Configuration()
    config.add(name='x',
               value=50,
               type_hint=int,
               description="test description")
    config.x = 'invalid_integer'
    with pytest.raises(ValidationFailureException):
        config.validate()


def test_add_condition():
    """
    Add condition to configuration and validate it, both with valid and invalid parameter values.
    """

    config = Configuration()
    config.add(name='x',
               value=[1, 2, 3],
               type_hint=List[int],
               description="test description")
    config.add(name='y',
               value=[2, 2, 2],
               type_hint=List[int],
               description="test description")
    config.add_condition(condition=lambda c: len(c.x) == len(c.y), name='x_y_pairing')
    config.validate()

    with pytest.raises(ValidationFailureException):
        config.x.append(5)
        config.validate()


def test_search_by_tag():
    """
    Search parameter by tag for quick retrieval
    """

    config = Configuration()
    config.add(name='x',
               value=5,
               tags={'number'})
    config.add(name='y',
               value=10,
               tags={'number'})
    config.add(name='z',
               value='z',
               tags={'letter'})

    result = config.search_param_by_tag(tags='number')
    assert 'x' in result
    assert 'y' in result
    assert type(result['x'] == int)
    assert type(result['y'] == int)


def test_search():
    """
    Search parameter via custom condition for quick retrieval
    """
    config = Configuration()
    config.add(name='x',
               value=5,
               tags={'number'})
    config.add(name='y',
               value=10,
               tags={'number'})
    config.add(name='z',
               value='z',
               tags={'letter'})

    result = config.search_param(conditions=[
        lambda param: 'number' in param.tags
    ])
    assert 'y' in result
    assert type(result['x'] == int)
    assert type(result['y'] == int)


def test_define_configuration(
        define_configuration
):
    """
    Define configuration via class and retrieve parameters
    """

    config = define_configuration
    assert config.x == 10
    assert config.get('x').value == 10
    assert config.get('x').name == 'x'

    config.x = 5
    assert config.x == 5
    assert config.get('x').value == 5


def test_validate_empty(
        define_configuration
):
    """
    Validate empty configuration successfully
    """

    config = define_configuration
    result = config.validate()
    assert result.passed is True


def test_type_hint_validation_nonstrict(
        define_configuration
):
    """
    Testing that typecheck condition triggers when setting a parameter to a new value with different type
    """

    config = define_configuration
    result = config.validate(strict=False)
    assert result.passed is True

    config.x = '10'

    result = config.validate(strict=False)
    assert result.passed is False
    assert result.error_message == 'Condition x_typecheck failed!'


def test_type_hint_validation_strict(
        define_configuration
):
    """
    Testing that configuration.validate() raises an exception when running in strict mode (default)
    """

    config = define_configuration
    config.validate()

    config.x = '10'
    with pytest.raises(ValidationFailureException):
        config.validate()


def test_required_validation():
    """
    Testing that 'is_required' parameter attribute triggers an exception when parameter.value is None
    """

    config = Configuration()
    config.add(name='x',
               is_required=True,
               type_hint=int,
               description='a parameter')
    with pytest.raises(ValidationFailureException):
        config.validate()


def test_allowed_range_validation():
    """
    Testing that configuration triggers an exception when parameter.value is not in parameter.allowed_range
    """

    config = Configuration()
    config.add(name='x',
               value=5,
               is_required=True,
               type_hint=int,
               allowed_range=lambda value: value in [1, 2, 3, 4, 5],
               description='a parameter')
    config.validate()

    config.x = 10
    assert config.validate(strict=False).passed is False


def test_variants_validation_exception():
    """
    Testing that an empty parameter.variants field is not allowed
    """

    config = Configuration()
    config.add(name='x',
               value=5,
               is_required=True,
               type_hint=int,
               variants=[],
               description='a parameter')
    with pytest.raises(ValidationFailureException):
        config.validate()


def test_copy():
    """
    Testing that a Config can be deep copied
    """

    config = Configuration()
    config.add(name='x',
               value=[1, 2, 3])
    config.add(name='y',
               value=Configuration(z=5))
    copy = deepcopy(config)
    copy.x.append(5)

    assert config.x == [1, 2, 3]
    assert copy.x == [1, 2, 3, 5]

    copy.y.z = 10
    assert config.y.z == 5
    assert copy.y.z == 10


def test_get_delta_copy():
    """
    Testing configuration.get_delta_copy()
    """

    config = Configuration()
    config.add(name='x',
               value=10,
               type_hint=int,
               description='a parameter')
    delta_copy: Configuration = config.delta_copy()
    config.x = 5
    assert delta_copy.x == 10
    assert config.x == 5
    assert type(delta_copy) == Configuration

    other_copy: Configuration = delta_copy.delta_copy(x=15)
    assert other_copy.x == 15
    assert delta_copy.x == 10
    assert config.x == 5
    assert type(other_copy) == Configuration

    other_copy.add(name='y',
                   value=0)
    assert 'y' not in config.params
    assert 'y' not in delta_copy.params
    assert other_copy.y == 0


def test_to_value_dict():
    config = Configuration()
    config.add(name='x',
               value=10,
               type_hint=int,
               description='a parameter')
    config.add(name='child',
               value=RegistrationKey(name='component', namespace='testing')
               )
    value_dict = config.to_value_dict()
    assert value_dict == {'x': 10}


def test_validate_nested_config():
    parent = Configuration()
    child = Configuration()
    child.add(name='y', value=5, allowed_range=lambda x: x < 3)

    parent.validate()

    parent.add(name='child', value=child)

    with pytest.raises(ValidationFailureException):
        child.validate(strict=True)

    with pytest.raises(ValidationFailureException):
        parent.validate(strict=True)
