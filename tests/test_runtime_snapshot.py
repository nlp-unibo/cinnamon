"""Handing a built registry to a process that did not build it.

A worker has to resolve keys and has no reason to scan anything. What it needs
is the answer a build arrived at -- which component each key names, and what
its configuration resolved to -- and not the machinery that arrived at it.
These pin that the answer travels, and that a value which cannot travel is
refused where it can still be attributed.
"""

import pickle
from multiprocessing import get_context

import pytest

from cinnamon.configuration import Configuration, Param
from cinnamon.registry import RegistrationKey, Registry
from cinnamon.utility.exceptions import (
    NotExpandedException,
    UnserializableRuntimeException,
)
from tests.fixtures import BaseComponent

NAMESPACE = "runtime"


class ChildConfig(Configuration):
    x: int = Param(1)
    y: int = Param(2)


class ParentConfig(Configuration):
    x: int = Param(3)
    y: int = Param(4)
    child: RegistrationKey | None = Param(None)


class LambdaConfig(Configuration):
    x: int = Param(5)
    y: int = Param(6)
    #: What a worker could never be handed, and the reason freezing checks.
    callback: object = Param(None)


def key(name: str) -> RegistrationKey:
    return RegistrationKey(name=name, namespace=NAMESPACE)


def register(name: str, config: Configuration) -> RegistrationKey:
    return Registry.register_configuration(
        config=config,
        name=name,
        namespace=NAMESPACE,
        component="tests.fixtures.BaseComponent",
    )


def expand() -> None:
    """What a build does at the end of one: no more registrations, and keys
    may now be resolved. Done by hand because these tests register first."""
    Registry.expanded = True


def build_in_worker(frozen_and_key):
    """What a spawned worker does: install, then build. No scan, no imports."""
    frozen, wanted = frozen_and_key
    Registry.install_runtime(frozen)
    component = Registry.from_key(wanted, expected_type=BaseComponent)
    return type(component).__name__, component.x, component.y


def test_a_frozen_runtime_survives_a_pickle_round_trip(reset_registry):
    register("plain", ChildConfig.default())
    expand()

    frozen = Registry.freeze_runtime()
    returned = pickle.loads(pickle.dumps(frozen))

    assert list(returned) == list(frozen)
    entry = returned[key("plain")]
    assert entry["component"] == "tests.fixtures.BaseComponent"
    assert entry["values"]["x"] == 1


def test_a_process_that_built_nothing_builds_from_an_installed_runtime(
    reset_registry,
):
    """The whole point: a worker resolves keys without scanning anything."""
    register("plain", ChildConfig.default())
    expand()
    frozen = Registry.freeze_runtime()

    with get_context("spawn").Pool(processes=1) as pool:
        name, x, y = pool.apply(build_in_worker, ((frozen, key("plain")),))

    assert (name, x, y) == ("BaseComponent", 1, 2)


def test_a_nested_dependency_builds_through_the_installed_runtime(
    reset_registry,
):
    """A key in a value resolves through the same registry, as it always did."""
    register("child", ChildConfig.default())
    parent = ParentConfig.default()
    parent.child = key("child")
    register("parent", parent)
    expand()

    frozen = pickle.loads(pickle.dumps(Registry.freeze_runtime()))
    Registry.install_runtime(frozen)

    child = Registry.from_key(Registry._REGISTRY[key("parent")].config.values["child"])
    assert (child.x, child.y) == (1, 2)


def test_expected_type_still_recognises_the_class(reset_registry):
    """Because the component travels as an import path, not as a class.

    A pickled class arrives as a second object, and `issubclass` against the
    one this interpreter defines would refuse it.
    """
    register("plain", ChildConfig.default())
    expand()
    Registry.install_runtime(pickle.loads(pickle.dumps(Registry.freeze_runtime())))

    assert Registry.from_key(key("plain"), expected_type=BaseComponent) is not None


def test_freezing_leaves_the_registry_it_read_alone(reset_registry):
    register("plain", ChildConfig.default())
    expand()
    before = dict(Registry._REGISTRY)

    Registry.freeze_runtime()

    assert Registry._REGISTRY == before
    assert Registry.expanded
    assert Registry.from_key(key("plain")) is not None


def test_a_value_that_cannot_travel_names_its_key_and_field(
    reset_registry,
):
    """Here, where there is a stack that says which registration it came from.

    Not in the worker, where the same failure is an unpickling error with
    nothing to attribute it to.
    """
    config = LambdaConfig.default()
    config.callback = lambda value: value
    register("closure", config)
    expand()

    with pytest.raises(UnserializableRuntimeException) as failure:
        Registry.freeze_runtime()

    assert failure.value.field == "callback"
    assert "closure" in str(failure.value.registration_key)


def test_an_unexpanded_registry_has_no_runtime_to_freeze(reset_registry):
    with pytest.raises(NotExpandedException):
        Registry.freeze_runtime()
