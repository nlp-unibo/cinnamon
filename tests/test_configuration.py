from copy import deepcopy
from typing import List

import pytest

from cinnamon.configuration import Configuration, ValidationFailureException, Param
from cinnamon.registry import RegistrationKey
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


def test_set_param_from_config():
    """
    Configuration parameters are mutable
    We attempt to change a parameter value from a config
    """

    config = Configuration()
    config.add(name='x',
               value=50,
               type_hint=int,
               description="test description")
    config.x = 20
    assert config.x == 20
    assert config.get('x').value == 20


def test_set_param_from_param():
    """
    Parameters are immutable.
    Raise an exception when we attempt to change a parameter value
    """
    param = Param(name='x', value=50)
    param.x = 20
    assert param.x == 20


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
    assert any(p.name == 'y' for p in result)
    assert any(p.name == 'x' for p in result)
    assert all(type(p.value) == int for p in result)


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
    assert any(p.name == 'y' for p in result)
    assert all(type(p.value) == int for p in result)


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


def test_modify_existing_configuration(
        define_configuration
):
    """
    A simple way to define new configurations is to modify existing ones
    """

    config = define_configuration
    config.x = 20
    assert config.x == 20
    assert config.get('x').value == 20


def test_validate_empty(
        define_configuration
):
    """
    Validate empty configuration successfully
    """

    config = define_configuration
    result = config.validate()
    assert result.passed is True


def test_required_validation():
    """
    Testing that 'is_required' parameter attribute triggers an exception when parameter.value is None
    """

    config = Configuration()
    config.add(name='x',
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
               value=10,
               is_required=True,
               type_hint=int,
               allowed_range=lambda value: value in [1, 2, 3, 4, 5],
               description='a parameter')
    assert config.validate(strict=False).passed is False


def test_copy():
    """
    Testing that a Config can be deep copied
    """

    config = Configuration()
    config.add(name='x',
               value=[1, 2, 3])
    dep_config = Configuration()
    dep_config.add(name='z', value=5)
    config.add(name='y',
               value=dep_config)
    copy = deepcopy(config)
    copy.x.append(5)

    assert config.x == [1, 2, 3]
    assert copy.x == [1, 2, 3, 5]


def test_get_delta_copy_built():
    """
    Testing configuration.get_delta_copy()
    """

    config = Configuration()
    config.add(name='x',
               value=10,
               type_hint=int,
               description='a parameter')
    delta_copy = config.delta_copy(x=5)
    assert config.x == 10
    assert delta_copy.x == 5
    assert type(delta_copy) == Configuration

    other_copy = delta_copy.delta_copy(x=15)
    assert other_copy.x == 15
    assert delta_copy.x == 5
    assert config.x == 10
    assert type(other_copy) == Configuration

    other_copy.add(name='y',
                   value=0)
    assert 'y' not in config.params
    assert 'y' not in delta_copy.params
    assert other_copy.y == 0


def test_get_delta_copy_built_nested():
    """
    Delta copy is not meant for hierarchy propagation
    """

    parent = Configuration()
    parent.add(name='x', value=5)
    child = Configuration()
    child.add(name='y', value=10)
    child.add(name='child', value=RegistrationKey(name='config', namespace='testing'))
    parent.add(name='child', value=child)

    delta_flat = parent.delta_copy(x=10)
    assert delta_flat.x == 10
    assert delta_flat.child.y == 10
    assert id(delta_flat.child) != id(child)

    delta_nested = parent.delta_copy(x=10, y=20)
    assert delta_nested.x == 10
    assert delta_nested.child.y == 10
    assert id(delta_nested.child) != id(child)
    assert id(delta_nested.child) != id(delta_flat.child)


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
    assert value_dict == {
        'x': 10,
        'child': config.child
    }


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


def test_configuration_variant_keys():
    config = Configuration()
    config.add(name='x', variants=[1, 2, 3])
    config.add(name='y', value=5)
    key = RegistrationKey(name='config', namespace='testing')

    for variant_kwargs, variant_indexes in zip(*config.variants):
        variant_key = key.from_variant(variant_kwargs=variant_kwargs,
                                       variant_indexes=variant_indexes)
        assert f'y{key.KEY_VALUE_SEPARATOR}5' not in variant_key.tags
        assert len(variant_key.tags) == 1
        assert variant_key.tags == {f'x{key.KEY_VALUE_SEPARATOR}{variant_kwargs["x"]}'}


def test_configuration_with_multiple_variant_keys():
    config = Configuration()
    config.add(name='x', variants=[1, 2, 3])
    config.add(name='z', variants=['a', 'b'])
    config.add(name='y', value=5)
    key = RegistrationKey(name='config', namespace='testing')

    for variant_kwargs, variant_indexes in zip(*config.variants):
        variant_key = key.from_variant(variant_kwargs=variant_kwargs,
                                       variant_indexes=variant_indexes)
        assert f'y{key.KEY_VALUE_SEPARATOR}5' not in variant_key.tags
        assert len(variant_key.tags) == 2
        assert f'x{key.KEY_VALUE_SEPARATOR}{variant_kwargs["x"]}' in variant_key.tags
        assert f'z{key.KEY_VALUE_SEPARATOR}{variant_kwargs["z"]}' in variant_key.tags

