"""Keys registered without tags, whatever tags their variants generated (#59).

Variant expansion adds tags such as ``x=2`` to the keys it derives. Those tags
describe a variant, not the registration, so an untagged search keeps the
variants of an untagged registration and drops a registration given a tag.
"""

from cinnamon.registry import Registry
from tests.fixtures import ChildConfig, ConfigWithVariants


def register():
    untagged = Registry.register_configuration(
        config=ConfigWithVariants.default(), name="config", namespace="testing"
    )
    tagged = Registry.register_configuration(
        config=ChildConfig.default(), name="config", tags={"t1"}, namespace="testing"
    )
    Registry.dag_resolution()
    return untagged, tagged


def test_an_untagged_search_keeps_generated_tags_and_drops_user_tags(
    reset_registry,
):
    untagged, tagged = register()

    keys = {str(key) for key in Registry.retrieve_keys(untagged=True)}

    assert keys == {
        str(untagged),
        str(untagged.from_variant({"x": 2})),
        str(untagged.from_variant({"x": 3})),
    }
    assert str(tagged) not in keys
    assert str(tagged.from_variant({"y": True})) not in keys


def test_user_tags_leave_out_what_variants_generated(reset_registry):
    untagged, tagged = register()

    assert Registry.retrieve_user_tags(untagged.from_variant({"x": 2})) == set()
    variant = tagged.from_variant({"y": True})
    assert variant.tags == {"t1", "y=True"}
    assert Registry.retrieve_user_tags(variant) == {"t1"}


def test_user_tags_travel_with_a_frozen_runtime(reset_registry):
    untagged, _ = register()

    Registry.install_runtime(Registry.freeze_runtime())

    assert len(Registry.retrieve_keys(untagged=True)) == 3
