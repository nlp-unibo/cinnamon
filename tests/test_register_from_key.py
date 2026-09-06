"""
``Registry.register_configuration_from_key`` -- issue #3.

``expand_configuration`` derived a variant key with ``key.from_variant(...)``,
then passed ``variant_key.name``, ``.tags`` and ``.namespace`` to
``register_configuration``, which assembled an equal key from them. Two objects
where one would do, once per variant configuration.

Measured before changing anything, on 200 configurations expanding to 4800 keys:
``RegistrationKey.__init__`` ran 9200 times during ``dag_resolution`` and now
runs 4600. The saving is about **1% of resolution** -- worth having, not worth
claiming as a speed-up. What the method is really for is that a caller holding a
key should not have to take it apart for a callee that puts it back together.

The behavioural difference is that the key is used as given, so it keeps its
``description`` and ``special_tags`` instead of starting from empty.
"""

import pytest

from cinnamon.configuration import Configuration, Param
from cinnamon.registry import RegistrationKey, Registry
from cinnamon.utility.exceptions import (
    AlreadyExpandedException,
    AlreadyRegisteredException,
)


class SimpleConfig(Configuration):
    value: int = Param(1, description="anything")


class VariedConfig(Configuration):
    value: int = Param(1, variants=[2, 3])


def test_registers_under_the_key_it_is_given(reset_registry):
    key = RegistrationKey(name="thing", tags={"a"}, namespace="testing")

    returned = Registry.register_configuration_from_key(
        config=SimpleConfig(), registration_key=key
    )

    assert returned is key, "the key was rebuilt rather than used"
    assert Registry.in_registry(key)
    assert Registry.retrieve_configuration(registration_key=key).value == 1


def test_the_registry_holds_that_exact_object(reset_registry):
    """Not merely an equal key.

    ``RegistrationKey`` hashes on name, namespace and tags, so an equal-but-
    separate key is indistinguishable through the mapping. Identity is the only
    way to show the second construction is gone.
    """
    key = RegistrationKey(name="thing", namespace="testing")

    Registry.register_configuration_from_key(
        config=SimpleConfig(), registration_key=key
    )

    stored = next(iter(Registry._REGISTRY))
    assert stored is key


def test_description_and_special_tags_survive(reset_registry):
    """What the rebuilt key dropped.

    ``register_configuration`` takes three fields, so anything else the caller
    had set on its key was lost. Nothing depended on that, but it made the two
    paths quietly different.
    """
    key = RegistrationKey(
        name="thing",
        namespace="testing",
        description="a described key",
        special_tags={"__custom"},
    )

    Registry.register_configuration_from_key(
        config=SimpleConfig(), registration_key=key
    )

    stored = next(iter(Registry._REGISTRY))
    assert stored.description == "a described key"
    assert "__custom" in stored.special_tags


def test_run_method_still_marks_the_key_runnable(reset_registry):
    key = RegistrationKey(name="thing", namespace="testing")

    Registry.register_configuration_from_key(
        config=SimpleConfig(),
        registration_key=key,
        component="components.Thing",
        run_method="run",
    )

    assert "__runnable" in key.special_tags
    assert Registry.retrieve_runnable_keys() == [key]


def test_a_duplicate_key_is_refused(reset_registry):
    key = RegistrationKey(name="thing", namespace="testing")
    Registry.register_configuration_from_key(
        config=SimpleConfig(), registration_key=key
    )

    with pytest.raises(AlreadyRegisteredException):
        Registry.register_configuration_from_key(
            config=SimpleConfig(),
            registration_key=RegistrationKey(name="thing", namespace="testing"),
        )


def test_refused_after_expansion(reset_registry):
    Registry.register_configuration_from_key(
        config=SimpleConfig(),
        registration_key=RegistrationKey(name="thing", namespace="testing"),
    )
    Registry.dag_resolution()

    with pytest.raises(AlreadyExpandedException):
        Registry.register_configuration_from_key(
            config=SimpleConfig(),
            registration_key=RegistrationKey(name="other", namespace="testing"),
        )


# -- the delegation --


def test_register_configuration_still_works(reset_registry):
    """The old entry point is now a two-line wrapper; it must behave the same.

    Keeping one implementation rather than two that have to agree: the field
    form builds the key and hands it on.
    """
    key = Registry.register_configuration(
        config=SimpleConfig(), name="thing", tags={"a"}, namespace="testing"
    )

    assert key == RegistrationKey(name="thing", tags={"a"}, namespace="testing")
    assert Registry.in_registry(key)


# -- what the issue was actually about --


def test_resolution_registers_variants_under_the_derived_key(reset_registry):
    """The variant key in the registry is the one resolution derived.

    Before, ``expand_configuration`` built the key, took it apart, and the
    registry ended up holding a second object assembled from the pieces.
    """
    Registry.register_configuration(
        config=VariedConfig(), name="varied", namespace="testing"
    )
    valid, _ = Registry.dag_resolution()

    variants = {key for key in valid if key.tags}
    assert len(variants) == 2

    stored = {id(key) for key in Registry._REGISTRY}
    assert {id(key) for key in variants} <= stored, (
        "resolution registered variants under keys other than the ones it derived"
    )


def test_resolution_builds_one_key_per_registration(reset_registry):
    """The count, which is the measurable part of issue #3.

    Two configurations with two variants each expand to six keys. Resolution
    used to construct twelve, one extra for every variant it registered.
    """
    for name in ("first", "second"):
        Registry.register_configuration(
            config=VariedConfig(), name=name, namespace="testing"
        )

    constructed = []
    original = RegistrationKey.__init__

    def counting_init(self, *args, **kwargs):
        constructed.append(1)
        original(self, *args, **kwargs)

    RegistrationKey.__init__ = counting_init
    try:
        valid, invalid = Registry.dag_resolution()
    finally:
        RegistrationKey.__init__ = original

    # Four variant keys are derived, and nothing rebuilds them.
    assert len(valid) + len(invalid) == 6
    assert len(constructed) == 4
