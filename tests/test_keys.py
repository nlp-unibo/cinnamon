import json
from pathlib import Path

from cinnamon.registry import RegistrationKey
from tests.fixtures import (
    ConfigWithChild,
    ConfigWithNonTaggableVariants,
    ConfigWithVariants,
)


def test_key_to_json():
    key = RegistrationKey(name="test", tags={"tag1", "tag2"}, namespace="testing")
    json_key = key.toJSON()
    assert json_key == (
        f"name{RegistrationKey.KEY_VALUE_SEPARATOR}test"
        f"{RegistrationKey.ATTRIBUTE_SEPARATOR}tags{RegistrationKey.KEY_VALUE_SEPARATOR}['tag1', 'tag2']"  # noqa: E501
        f"{RegistrationKey.ATTRIBUTE_SEPARATOR}namespace{RegistrationKey.KEY_VALUE_SEPARATOR}testing"
    )
    assert RegistrationKey.parse(json_key) == key


def test_key_json_serialization():
    key = RegistrationKey(name="test", tags={"tag1", "tag2"}, namespace="testing")
    json_file = Path("tmp.json")
    with json_file.open("w") as f:
        json.dump(key.toJSON(), f)
    with json_file.open("r") as f:
        json_data = json.load(f)

    loaded_key = RegistrationKey.parse(registration_key=json_data)
    assert loaded_key == key

    json_file.unlink()


def test_from_variant():
    base_key = RegistrationKey(name="config", namespace="testing")
    variant_kwargs = {"x": 1}
    variant_key = base_key.from_variant(variant_kwargs=variant_kwargs)
    assert variant_key == RegistrationKey(
        name="config", tags={"x=1"}, namespace="testing"
    )


def test_from_variant_with_key_and_conflicting_param():
    base_key = RegistrationKey(name="config", namespace="testing")
    key = RegistrationKey(name="config", tags={"x=1"}, namespace="testing")
    variant_kwargs = {"key": key, "x": 2}
    variant_key = base_key.from_variant(variant_kwargs=variant_kwargs)
    assert variant_key == RegistrationKey(
        name="config", tags={"x=2", "key.x=1"}, namespace="testing"
    )


def test_from_variant_with_multiple_keys():
    base_key = RegistrationKey(name="config", namespace="testing")
    key = RegistrationKey(name="config", tags={"x=1"}, namespace="testing")
    other_key = RegistrationKey(name="config", tags={"x=2", "y=1"}, namespace="testing")
    variant_kwargs = {"key": key, "other_key": other_key, "x": 2}
    variant_key = base_key.from_variant(variant_kwargs=variant_kwargs)
    assert variant_key == RegistrationKey(
        name="config",
        tags={"x=2", "key.x=1", "other_key.x=2", "other_key.y=1"},
        namespace="testing",
    )


def test_from_config_variants_with_taggable_params():
    config = ConfigWithVariants.default()
    config_key = RegistrationKey(name="config", namespace="testing")

    for variant_info in config.variants:
        variant_key = config_key.from_variant(
            variant_kwargs=variant_info['values'],
            variant_indexes=variant_info['indexes']
        )

        if variant_info['indexes']['x'] != 0:
            assert variant_key.tags == {
                f"x{config_key.KEY_VALUE_SEPARATOR}{variant_info['values']['x']}"
            }


def test_from_config_variants_with_non_taggable_params():
    config = ConfigWithNonTaggableVariants.default()
    config_key = RegistrationKey(name="config", namespace="testing")

    for variant_info in config.variants:
        variant_key = config_key.from_variant(
            variant_kwargs=variant_info['values'],
            variant_indexes=variant_info['indexes']
        )

        assert variant_key.tags == {f"x{config_key.KEY_VALUE_SEPARATOR}variant-1"}


def test_tags_simplification():
    key = RegistrationKey(name="test", tags={"x", "y", "z"}, namespace="testing")
    simplified_key = key.from_tags_simplification({"x", "y"})

    assert len(simplified_key.tags) == 1
    assert simplified_key.tags == {"z"}
    assert simplified_key.name == key.name
    assert simplified_key.namespace == key.namespace


def test_key_pydantic_serializable():
    config = ConfigWithChild()
    config_json = config.model_dump_json()
    assert config_json == '{"c1":"name=test--tags=[\'t2\']--namespace=testing"}'