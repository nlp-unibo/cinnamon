import json
from pathlib import Path

from cinnamon.registry import RegistrationKey


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
