import json
from pathlib import Path

from cinnamon.registry import RegistrationKey
from cinnamon.configuration import Configuration


def test_key_to_json():
    key = RegistrationKey(name='test', tags={'tag1', 'tag2'}, namespace='testing')
    json_key = key.toJSON()
    assert json_key == (f"name{RegistrationKey.KEY_VALUE_SEPARATOR}test"
                        f"{RegistrationKey.ATTRIBUTE_SEPARATOR}tags{RegistrationKey.KEY_VALUE_SEPARATOR}['tag1', 'tag2']"
                        f"{RegistrationKey.ATTRIBUTE_SEPARATOR}namespace{RegistrationKey.KEY_VALUE_SEPARATOR}testing")
    assert RegistrationKey.parse(json_key) == key


def test_key_json_serialization():
    key = RegistrationKey(name='test', tags={'tag1', 'tag2'}, namespace='testing')
    json_file = Path('tmp.json')
    with json_file.open('w') as f:
        json.dump(key.toJSON(), f)
    with json_file.open('r') as f:
        json_data = json.load(f)

    loaded_key = RegistrationKey.parse(registration_key=json_data)
    assert loaded_key == key

    json_file.unlink()


def test_from_variant():
    base_key = RegistrationKey(name='config', namespace='testing')
    variant_kwargs = {
        'x': 1
    }
    variant_key = base_key.from_variant(variant_kwargs=variant_kwargs)
    assert variant_key == RegistrationKey(name='config',
                                          tags={'x=1'},
                                          namespace='testing')


def test_from_variant_with_key_and_conflicting_param():
    base_key = RegistrationKey(name='config', namespace='testing')
    key = RegistrationKey(name='config', tags={'x=1'}, namespace='testing')
    variant_kwargs = {
        'key': key,
        'x': 2
    }
    variant_key = base_key.from_variant(variant_kwargs=variant_kwargs)
    assert variant_key == RegistrationKey(name='config',
                                          tags={'x=2', 'key.x=1'},
                                          namespace='testing')


def test_from_variant_with_multiple_keys():
    base_key = RegistrationKey(name='config', namespace='testing')
    key = RegistrationKey(name='config', tags={'x=1'}, namespace='testing')
    other_key = RegistrationKey(name='config', tags={'x=2', 'y=1'}, namespace='testing')
    variant_kwargs = {
        'key': key,
        'other_key': other_key,
        'x': 2
    }
    variant_key = base_key.from_variant(variant_kwargs=variant_kwargs)
    assert variant_key == RegistrationKey(name='config',
                                          tags={'x=2', 'key.x=1', 'other_key.x=2', 'other_key.y=1'},
                                          namespace='testing')


def test_from_config_variants_with_taggable_params():
    config = Configuration()
    config.add(name='x', value=5, variants=[1])
    config_key = RegistrationKey(name='config', namespace='testing')

    for variant_kwargs, variant_indexes in zip(*config.variants):
        variant_key = config_key.from_variant(variant_kwargs=variant_kwargs,
                                              variant_indexes=variant_indexes)
        variant_config = config.delta_copy(**variant_kwargs)

        if variant_config == config:
            continue

        assert variant_key.tags == {f'x{config_key.KEY_VALUE_SEPARATOR}1'}


def test_from_config_variants_with_non_taggable_params():
    config = Configuration()
    config.add(name='x', value=[1, 2, 3], variants=[[2, 2]])
    config_key = RegistrationKey(name='config', namespace='testing')

    for variant_kwargs, variant_indexes in zip(*config.variants):
        variant_key = config_key.from_variant(variant_kwargs=variant_kwargs,
                                              variant_indexes=variant_indexes)
        variant_config = config.delta_copy(**variant_kwargs)

        if variant_config == config:
            assert variant_key.tags == {f'x{config_key.KEY_VALUE_SEPARATOR}default-value'}
            continue

        assert variant_key.tags == {f'x{config_key.KEY_VALUE_SEPARATOR}variant-1'}