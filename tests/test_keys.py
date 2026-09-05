import json

import pytest

from cinnamon.registry import RegistrationKey, json_default
from cinnamon.utility.registration import match_tags
from tests.fixtures import (
    ConfigWithChild,
    ConfigWithNonTaggableVariants,
    ConfigWithVariants,
)


def test_key_string_form():
    """str(key) is the canonical, parseable serialization of a key."""
    key = RegistrationKey(name="test", tags={"tag1", "tag2"}, namespace="testing")
    assert str(key) == (
        f"name{RegistrationKey.KEY_VALUE_SEPARATOR}test"
        f"{RegistrationKey.ATTRIBUTE_SEPARATOR}tags"
        f"{RegistrationKey.KEY_VALUE_SEPARATOR}['tag1', 'tag2']"
        f"{RegistrationKey.ATTRIBUTE_SEPARATOR}namespace"
        f"{RegistrationKey.KEY_VALUE_SEPARATOR}testing"
    )
    assert RegistrationKey.parse(str(key)) == key


def test_key_survives_a_json_round_trip(tmp_path):
    """A key's string form can be stored as JSON and parsed back."""
    key = RegistrationKey(name="test", tags={"tag1", "tag2"}, namespace="testing")
    json_file = tmp_path / "keys.json"

    json_file.write_text(json.dumps(str(key)))
    loaded_key = RegistrationKey.parse(
        registration_key=json.loads(json_file.read_text())
    )

    assert loaded_key == key


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
            variant_kwargs=variant_info["values"],
            variant_indexes=variant_info["indexes"],
        )

        if variant_info["indexes"]["x"] != 0:
            assert variant_key.tags == {
                f"x{config_key.KEY_VALUE_SEPARATOR}{variant_info['values']['x']}"
            }


def test_from_config_variants_with_non_taggable_params():
    config = ConfigWithNonTaggableVariants.default()
    config_key = RegistrationKey(name="config", namespace="testing")

    for variant_info in config.variants:
        variant_key = config_key.from_variant(
            variant_kwargs=variant_info["values"],
            variant_indexes=variant_info["indexes"],
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


def test_from_string():
    key_str = "name=test--tags=[]--namespace=testing"
    key = RegistrationKey.from_string(key_str)
    assert key.name == "test"
    assert key.namespace == "testing"
    assert key.tags == set()


def test_from_string_with_tags():
    key_str = "name=test--tags=['x=1']--namespace=testing"
    key = RegistrationKey.from_string(key_str)
    assert key.name == "test"
    assert key.namespace == "testing"
    assert key.tags == {"x=1"}


# -- immutability --


def test_key_name_immutable():
    key = RegistrationKey(name="test", namespace="testing")
    with pytest.raises(AttributeError):
        key.name = "other"


def test_key_namespace_immutable():
    key = RegistrationKey(name="test", namespace="testing")
    with pytest.raises(AttributeError):
        key.namespace = "other"


def test_key_tags_immutable():
    key = RegistrationKey(name="test", namespace="testing")
    with pytest.raises(AttributeError):
        key.tags = {"other"}


# -- equality / check helpers --


def test_key_eq_not_registration_key():
    key = RegistrationKey(name="test", namespace="testing")
    assert key != "test"
    assert key != None  # noqa: E711


def test_key_eq_different_tags():
    a = RegistrationKey(name="test", tags={"t1"}, namespace="testing")
    b = RegistrationKey(name="test", tags={"t2"}, namespace="testing")
    assert a != b
    assert a.check_tags(b.tags) is False


def test_key_eq_different_name():
    a = RegistrationKey(name="test", namespace="testing")
    b = RegistrationKey(name="other", namespace="testing")
    assert a != b
    assert a.check_name(b.name) is False


def test_key_check_namespace_false():
    a = RegistrationKey(name="test", namespace="testing")
    b = RegistrationKey(name="test", namespace="other")
    assert a.check_namespace(b.namespace) is False


# -- match (key-vs-key tag subset) --


def test_key_match_tag_intersection():
    key = RegistrationKey(name="test", tags={"a", "b", "c"}, namespace="testing")
    other = RegistrationKey(name="test", tags={"b", "c", "d"}, namespace="testing")
    assert key.match(other, {"b", "c"})
    assert not key.match(other, {"d"})


# -- compound / hierarchy tags --


def test_compound_tags():
    key = RegistrationKey(name="test", tags={"x=1", "plain"}, namespace="testing")
    assert key.compound_tags == {"x=1"}


def test_hierarchy_tags():
    key = RegistrationKey(name="test", tags={"child.x=1", "plain"}, namespace="testing")
    assert key.hierarchy_tags == {"child.x=1"}


# -- pretty string wrap --


def test_pretty_string_multiple_tag_lines():
    key = RegistrationKey(
        name="test", tags={f"t{i}" for i in range(7)}, namespace="testing"
    )
    pretty = key.to_pretty_string()
    tags_section = pretty.split("tags:")[1].split("namespace:")[0]
    tag_lines = [ln for ln in tags_section.split("\n") if ln.strip()]
    assert len(tag_lines) > 1


def test_pretty_string_single_tag_line():
    key = RegistrationKey(name="test", tags={"t1"}, namespace="testing")
    pretty = key.to_pretty_string()
    tags_section = pretty.split("tags:")[1].split("namespace:")[0]
    tag_lines = [ln for ln in tags_section.split("\n") if ln.strip()]
    assert len(tag_lines) == 1


# -- parse / from_string failure paths --


@pytest.mark.parametrize(
    "malformed",
    ["", "garbage", "name=only", "--namespace=testing", "tags=['a']--namespace=ns"],
)
def test_from_string_malformed_raises(malformed):
    with pytest.raises(ValueError):
        RegistrationKey.from_string(malformed)


def test_parse_no_args_raises():
    with pytest.raises(AttributeError):
        RegistrationKey.parse()


def test_parse_unsupported_key_type_raises():
    with pytest.raises(AttributeError):
        RegistrationKey.parse(registration_key=12345)


# -- match_tags (registration.tag matching) --


def test_match_tags_none_filter_is_true():
    assert match_tags(a_tags={"t1"}, b_tags=None) is True


def test_match_tags_empty_a_and_none_b():
    # empty a_tags + b containing None => match
    assert match_tags(a_tags=set(), b_tags={None}) is True


def test_match_tags_removes_none_from_b():
    # non-empty a_tags + None in b_tags => None is removed, then subset check
    a = {"t1", "t2"}
    b = {"t1", "t2", None}
    assert match_tags(a_tags=a, b_tags=set(b)) is True


def test_match_tags_subset_match():
    assert match_tags(a_tags={"t1", "t2"}, b_tags={"t1"}) is True


def test_match_tags_no_match():
    assert match_tags(a_tags={"t1"}, b_tags={"t2"}) is False


# -- serialization ----------------------------------------------------------


def test_to_dict_is_plain_json_data():
    key = RegistrationKey(name="loader", tags={"v2", "imdb"}, namespace="nlp")

    assert key.to_dict() == {
        "name": "loader",
        "namespace": "nlp",
        "tags": ["imdb", "v2"],  # sorted, so the output is stable
    }
    assert json.dumps(key.to_dict())  # no encoder needed


def test_to_dict_is_order_stable():
    """Two keys built from the same tags in different order serialize alike."""
    first = RegistrationKey(name="a", tags={"x", "y"}, namespace="ns")
    second = RegistrationKey(name="a", tags={"y", "x"}, namespace="ns")

    assert first.to_dict() == second.to_dict()


def test_from_dict_round_trips():
    key = RegistrationKey(name="loader", tags={"imdb", "v2"}, namespace="nlp")

    assert RegistrationKey.from_dict(key.to_dict()) == key


def test_from_dict_accepts_a_minimal_mapping():
    key = RegistrationKey.from_dict({"name": "solo"})

    assert key.name == "solo"
    assert key.namespace == "default"
    assert key.tags == frozenset()


def test_from_dict_requires_a_name():
    with pytest.raises(ValueError, match="needs a name"):
        RegistrationKey.from_dict({"namespace": "nlp"})


def test_json_default_serializes_nested_keys():
    """Keys anywhere inside a structure, which is what containers produce."""
    first = RegistrationKey(name="a", namespace="ns")
    second = RegistrationKey(name="b", tags={"t"}, namespace="ns")

    encoded = json.dumps(
        {"losses": [first, second], "metric": {"acc": first}}, default=json_default
    )
    decoded = json.loads(encoded)

    assert [RegistrationKey.from_dict(item) for item in decoded["losses"]] == [
        first,
        second,
    ]
    assert RegistrationKey.from_dict(decoded["metric"]["acc"]) == first


def test_json_default_leaves_other_types_to_fail():
    """It must not swallow genuinely unserializable objects."""
    with pytest.raises(TypeError, match="not JSON serializable"):
        json.dumps({"when": object()}, default=json_default)


# -- string round trip ------------------------------------------------------


@pytest.mark.parametrize(
    "key",
    [
        RegistrationKey(name="n", namespace="ns"),
        RegistrationKey(name="n", tags={"a", "b"}, namespace="ns"),
        # every component may legitimately contain the attribute separator
        RegistrationKey(name="n", tags={"a--b"}, namespace="ns"),
        RegistrationKey(name="a--b", namespace="ns"),
        RegistrationKey(name="n", namespace="a--b"),
        # ... and the key/value separator, and the hierarchy separator
        RegistrationKey(name="n", tags={"x=1", "y.z"}, namespace="ns"),
        RegistrationKey(name="n", tags={"[weird]"}, namespace="ns"),
    ],
    ids=lambda key: str(key),
)
def test_string_form_round_trips(key):
    """Regression: splitting on '--' cut a tag containing it in half.

    ``tags={'a--b'}`` produced ``name=n--tags=['a--b']--namespace=ns``, which
    split into four pieces and then failed to evaluate ``"['a"``.
    """
    assert RegistrationKey.from_string(str(key)) == key


def test_unreadable_tags_report_the_key():
    with pytest.raises(ValueError, match="Could not read the tags"):
        RegistrationKey.from_string("name=n--tags=[1//2]--namespace=ns")
