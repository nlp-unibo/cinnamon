import json
from pathlib import Path
import pytest

from cinnamon.registry import RegistrationKey
from cinnamon.utility.exceptions import TagConflictException


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


def test_trigger_tag_conflict_with_flat_param_and_key():
    base_key = RegistrationKey(name='config', tags={'x=1'}, namespace='testing')
    key = RegistrationKey(name='config', tags={'x=1'}, namespace='testing')
    variant_kwargs = {
        'key': key,
        'x': 2
    }
    with pytest.raises(TagConflictException):
        variant_key = base_key.from_variant(variant_kwargs=variant_kwargs)


# TODO: test when we have two keys that might lead to tag conflict
def test_from_variant_with_multiple_conflicts():
    pass
