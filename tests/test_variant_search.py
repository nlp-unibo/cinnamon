"""Searching keys by the values of their variant parameters (issue #76).

A variant parameter adds a tag only for its non-default values, so a tag
search cannot select a default. The registry therefore records the value of
every variant parameter of a key, its default included, and ``retrieve_keys``
searches those values. Keys keep their string form: nothing here renames one.
"""

from cinnamon.configuration import Configuration
from cinnamon.registry import Registry
from tests.fixtures import (
    ChildConfig,
    ConfigWithMultipleVariants,
    VariantConfigWithChild,
)


def register_two_parameters():
    """``x`` in 1, 2, 3 and ``y`` in 2, 3, 4: nine keys, defaults ``x=1, y=2``."""
    key = Registry.register_configuration(
        config=ConfigWithMultipleVariants.default(), name="config", namespace="testing"
    )
    Registry.dag_resolution()
    return key


def found(**variants):
    return {
        str(key) for key in Registry.retrieve_keys(names="config", variants=variants)
    }


def test_a_default_value_is_searchable(reset_registry):
    key = register_two_parameters()

    assert found(x=1) == {
        str(key),
        str(key.from_variant({"y": 3})),
        str(key.from_variant({"y": 4})),
    }


def test_a_non_default_value_is_searchable(reset_registry):
    key = register_two_parameters()

    assert found(x=2) == {
        str(key.from_variant({"x": 2})),
        str(key.from_variant({"x": 2, "y": 3}, {"x": 1, "y": 1})),
        str(key.from_variant({"x": 2, "y": 4}, {"x": 1, "y": 2})),
    }


def test_a_default_and_a_non_default_value_combine(reset_registry):
    key = register_two_parameters()

    assert found(x=3, y=2) == {str(key.from_variant({"x": 3}))}
    assert found(x=1, y=2) == {str(key)}
    assert found(x=1, y=5) == set()


def test_no_variant_filter_keeps_every_key(reset_registry):
    register_two_parameters()

    assert len(found()) == 9


def test_a_key_keeps_its_string_form(reset_registry):
    """The values sit beside the key, so the base key is still untagged."""
    key = register_two_parameters()

    assert str(key) == "name=config--namespace=testing"
    assert Registry.retrieve_variant_values(key) == {"x": 1, "y": 2}


def test_a_dotted_name_reads_the_variant_parameter_of_a_child(reset_registry):
    parent = Registry.register_configuration(
        config=VariantConfigWithChild.default(), name="config", namespace="testing"
    )
    child = Registry.register_configuration(
        config=ChildConfig.default(), name="test", tags={"t2"}, namespace="testing"
    )
    Registry.dag_resolution()

    keys = Registry.retrieve_keys(names="config", variants={"c1.y": False})
    assert {str(key) for key in keys} == {
        str(parent),
        str(parent.from_variant({"x": 2})),
        str(parent.from_variant({"x": 3})),
    }
    assert Registry.retrieve_variant_values(child) == {"y": False}


def test_a_dotted_name_through_a_value_that_is_not_a_key_matches_nothing(
    reset_registry,
):
    register_two_parameters()

    assert found(**{"x.y": 1}) == set()


def test_an_unknown_parameter_matches_nothing(reset_registry):
    register_two_parameters()

    assert found(z=1) == set()


def test_a_key_without_variant_parameters_has_no_values(reset_registry):
    key = Registry.register_configuration(
        config=Configuration.default(), name="leaf", namespace="testing"
    )
    Registry.dag_resolution()

    assert Registry.retrieve_variant_values(key) == {}
    assert Registry.retrieve_keys(names="leaf", variants={"x": 1}) == []


def test_the_values_travel_with_a_frozen_runtime(reset_registry):
    key = register_two_parameters()
    frozen = Registry.freeze_runtime()

    Registry.install_runtime(frozen)

    assert Registry.retrieve_variant_values(key) == {"x": 1, "y": 2}
    assert len(found(x=1)) == 3
