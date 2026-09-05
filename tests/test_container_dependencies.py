"""
Dependencies declared as flat containers of registration keys.

A dependency field may hold a single ``RegistrationKey``, a ``list`` of them, or
a ``dict`` of them. These tests pin the behaviour that distinguishes containers
from the long-standing scalar case: edge building, expansion, resolution, the
shape a component actually receives, and the deliberate limits.
"""

from typing import Any, Dict, List, Optional, Union

import pytest

from cinnamon.configuration import Configuration, Param
from cinnamon.registry import RegistrationKey, Registry
from cinnamon.utility.dependencies import (
    DependencyShape,
    iter_dependency_keys,
    map_dependency_keys,
)

NAMESPACE = "containers"

CE = RegistrationKey(name="ce", namespace=NAMESPACE)
SPARSITY = RegistrationKey(name="sparsity", namespace=NAMESPACE)
ACCURACY = RegistrationKey(name="accuracy", namespace=NAMESPACE)
PARENT = RegistrationKey(name="model", namespace=NAMESPACE)


class LeafConfig(Configuration):
    weight: float = 1.0


class VariedLeafConfig(Configuration):
    weight: float = Param(1.0, variants=[2.0, 3.0])


class LeafComponent:
    def __init__(self, weight: float = 1.0):
        self.weight = weight


class ModelComponent:
    """Receives keys and builds its own children, as a real component does."""

    def __init__(self, losses=None, metrics=None):
        self.losses = losses
        self.metrics = metrics


def _register_leaves(config_class=LeafConfig):
    for name in ("ce", "sparsity", "accuracy"):
        Registry.register_configuration(
            config=config_class(),
            name=name,
            namespace=NAMESPACE,
            component="tests.test_container_dependencies.LeafComponent",
        )


def _child_keys(key):
    return sorted(str(edge[1]) for edge in Registry._DEPENDENCY_DAG.out_edges(key))


# -- detection --------------------------------------------------------------


def test_iter_dependency_keys_handles_every_shape():
    assert list(iter_dependency_keys(CE)) == [CE]
    assert list(iter_dependency_keys([CE, SPARSITY])) == [CE, SPARSITY]
    assert list(iter_dependency_keys({"a": CE, "b": SPARSITY})) == [CE, SPARSITY]
    assert list(iter_dependency_keys(None)) == []
    assert list(iter_dependency_keys(7)) == []
    # partially resolved containers iterate cleanly
    assert list(iter_dependency_keys([CE, LeafConfig()])) == [CE]


def test_map_dependency_keys_preserves_shape():
    assert map_dependency_keys(CE, lambda key: key.name) == "ce"
    assert map_dependency_keys([CE, SPARSITY], lambda key: key.name) == [
        "ce",
        "sparsity",
    ]
    assert map_dependency_keys({"x": CE}, lambda key: key.name) == {"x": "ce"}
    assert map_dependency_keys((CE,), lambda key: key.name) == ("ce",)
    assert map_dependency_keys(None, lambda key: key.name) is None


# -- registration and the DAG ----------------------------------------------


def test_list_dependency_adds_one_edge_per_member(reset_registry):
    class ModelConfig(Configuration):
        losses: List[RegistrationKey] = [CE, SPARSITY]

    _register_leaves()
    Registry.register_configuration(
        config=ModelConfig(), name="model", namespace=NAMESPACE
    )

    assert _child_keys(PARENT) == [str(CE), str(SPARSITY)]


def test_dict_dependency_adds_one_edge_per_value(reset_registry):
    class ModelConfig(Configuration):
        metrics: Dict[str, RegistrationKey] = {"acc": ACCURACY, "loss": CE}

    _register_leaves()
    Registry.register_configuration(
        config=ModelConfig(), name="model", namespace=NAMESPACE
    )

    assert _child_keys(PARENT) == [str(ACCURACY), str(CE)]


def test_unset_optional_container_registers_without_edges(reset_registry):
    """An optional dependency left at None is legal and contributes no edges."""

    class ModelConfig(Configuration):
        metrics: Optional[Dict[str, RegistrationKey]] = None
        losses: List[RegistrationKey] = []

    Registry.register_configuration(
        config=ModelConfig(), name="model", namespace=NAMESPACE
    )

    assert list(ModelConfig().dependencies) == ["metrics", "losses"]
    assert _child_keys(PARENT) == []


def test_shared_member_is_a_single_node(reset_registry):
    """Two parents depending on the same key share one node."""

    class FirstConfig(Configuration):
        losses: List[RegistrationKey] = [CE]

    class SecondConfig(Configuration):
        losses: List[RegistrationKey] = [CE]

    _register_leaves()
    Registry.register_configuration(FirstConfig(), name="first", namespace=NAMESPACE)
    Registry.register_configuration(SecondConfig(), name="second", namespace=NAMESPACE)

    first = RegistrationKey(name="first", namespace=NAMESPACE)
    second = RegistrationKey(name="second", namespace=NAMESPACE)
    assert _child_keys(first) == _child_keys(second) == [str(CE)]
    assert sum(1 for node in Registry._DEPENDENCY_DAG.nodes if node == CE) == 1


# -- resolution and instantiation ------------------------------------------


def test_resolution_preserves_container_shape(reset_registry):
    class ModelConfig(Configuration):
        losses: List[RegistrationKey] = [CE, SPARSITY]
        metrics: Dict[str, RegistrationKey] = {"acc": ACCURACY}

    _register_leaves()
    Registry.register_configuration(ModelConfig(), name="model", namespace=NAMESPACE)
    Registry.dag_resolution()

    config = Registry.retrieve_configuration(registration_key=PARENT)
    resolved = Registry.resolve_configuration(config=config.model_copy(deep=True))

    assert [type(item) for item in resolved.losses] == [LeafConfig, LeafConfig]
    assert list(resolved.metrics) == ["acc"]
    assert isinstance(resolved.metrics["acc"], LeafConfig)


def test_component_receives_raw_keys_in_container_shape(reset_registry):
    """Components get keys, not configurations, and build their own children.

    ``Registry.instantiate`` passes the registered configuration's values
    straight through, so a component is free to call ``Registry.from_key`` on
    each member -- which is what makes lazily-built children possible.
    """

    class ModelConfig(Configuration):
        losses: List[RegistrationKey] = [CE, SPARSITY]
        metrics: Dict[str, RegistrationKey] = {"acc": ACCURACY}

    _register_leaves()
    Registry.register_configuration(
        config=ModelConfig(),
        name="model",
        namespace=NAMESPACE,
        component="tests.test_container_dependencies.ModelComponent",
    )
    Registry.dag_resolution()

    component = Registry.instantiate(registration_key=PARENT)

    assert component.losses == [CE, SPARSITY]
    assert component.metrics == {"acc": ACCURACY}
    assert isinstance(Registry.from_key(component.losses[0]), LeafComponent)


# -- variants ---------------------------------------------------------------


def test_whole_container_variants_produce_parent_keys(reset_registry):
    """A container field varies as a whole container."""

    class ModelConfig(Configuration):
        losses: List[RegistrationKey] = Param([CE], variants=[[CE, SPARSITY]])

    _register_leaves()
    Registry.register_configuration(ModelConfig(), name="model", namespace=NAMESPACE)
    valid_keys, _ = Registry.dag_resolution()

    variant = RegistrationKey(
        name="model", tags={"losses=variant-1"}, namespace=NAMESPACE
    )
    assert variant in valid_keys

    variant_config = Registry.retrieve_configuration(registration_key=variant)
    assert variant_config.losses == [CE, SPARSITY]


def test_member_variants_are_registered_but_do_not_vary_the_parent(reset_registry):
    """The documented asymmetry between scalar and container dependencies.

    A scalar dependency propagates its child's variants upward, giving the
    parent one variant per child variant. A container deliberately does not:
    doing so would mean a cartesian product across members, so a container
    varies only through variants the user declares on the whole field.
    """

    class ModelConfig(Configuration):
        losses: List[RegistrationKey] = [CE]

    Registry.register_configuration(VariedLeafConfig(), name="ce", namespace=NAMESPACE)
    Registry.register_configuration(ModelConfig(), name="model", namespace=NAMESPACE)
    valid_keys, _ = Registry.dag_resolution()

    # the member's own variants are registered and usable
    assert (
        RegistrationKey(name="ce", tags={"weight=2.0"}, namespace=NAMESPACE)
        in valid_keys
    )
    # ... but the parent has exactly one key
    assert [key for key in valid_keys if key.name == "model"] == [PARENT]


def test_scalar_dependency_still_propagates_child_variants(reset_registry):
    """The contrast case, so the asymmetry above cannot regress unnoticed."""

    class ModelConfig(Configuration):
        loss: RegistrationKey = CE

    Registry.register_configuration(VariedLeafConfig(), name="ce", namespace=NAMESPACE)
    Registry.register_configuration(ModelConfig(), name="model", namespace=NAMESPACE)
    valid_keys, _ = Registry.dag_resolution()

    model_tags = sorted(sorted(key.tags) for key in valid_keys if key.name == "model")
    assert model_tags == [[], ["loss.weight=2.0"], ["loss.weight=3.0"]]


# -- limits -----------------------------------------------------------------


def test_nested_containers_are_rejected_at_registration(reset_registry):
    class NestedConfig(Configuration):
        losses: List[List[RegistrationKey]] = []

    with pytest.raises(TypeError, match="Nested containers"):
        Registry.register_configuration(
            NestedConfig(), name="model", namespace=NAMESPACE
        )


def test_non_key_member_is_rejected_at_registration(reset_registry):
    class InlineConfig(Configuration):
        losses: List[Configuration] = [LeafConfig()]

    with pytest.raises(TypeError, match="where a RegistrationKey was expected"):
        Registry.register_configuration(
            InlineConfig(), name="model", namespace=NAMESPACE
        )


def test_union_of_scalar_and_list_follows_the_value(reset_registry):
    """``RegistrationKey | list[RegistrationKey]`` resolves by what it holds."""

    class ModelConfig(Configuration):
        selectors: Union[RegistrationKey, List[RegistrationKey]] = CE

    scalar = ModelConfig()
    listed = ModelConfig(selectors=[CE, SPARSITY])
    field = scalar.fields["selectors"]

    assert (
        scalar.dependency_shape(field_name="selectors", field=field)
        is DependencyShape.SCALAR
    )
    assert (
        listed.dependency_shape(field_name="selectors", field=field)
        is DependencyShape.LIST
    )

    _register_leaves()
    Registry.register_configuration(listed, name="model", namespace=NAMESPACE)
    assert _child_keys(PARENT) == [str(CE), str(SPARSITY)]


def test_registration_key_rejects_non_string_coercion():
    """The pydantic validator must fail cleanly so unions can fall through."""

    class ScalarOnly(Configuration):
        child: RegistrationKey = CE

    with pytest.raises(Exception, match="Cannot build a RegistrationKey"):
        ScalarOnly(child=[CE])


def test_optional_scalar_dependency_left_unset(reset_registry):
    """A scalar dependency at None expands to nothing rather than failing."""

    class ModelConfig(Configuration):
        loss: Optional[RegistrationKey] = None

    Registry.register_configuration(ModelConfig(), name="model", namespace=NAMESPACE)
    valid_keys, _ = Registry.dag_resolution()

    assert PARENT in valid_keys
    assert _child_keys(PARENT) == []


def test_optional_container_annotation_survives_the_none_member():
    """``Optional[...]`` unwraps past NoneType to classify the real member."""

    class ModelConfig(Configuration):
        losses: Optional[List[RegistrationKey]] = None

    config = ModelConfig()
    shape = config.dependency_shape(field_name="losses", field=config.fields["losses"])
    assert shape is DependencyShape.LIST


def test_union_without_any_key_member_is_not_a_dependency():
    """A union of ordinary types is left alone."""

    class ModelConfig(Configuration):
        threshold: Union[int, str] = 1
        # NoneType is skipped while scanning union members, not mistaken for one
        limit: Optional[int] = None

    assert ModelConfig().dependencies == {}


def test_dict_of_plain_values_is_not_a_dependency():
    """Only dicts whose values are keys count."""

    class ModelConfig(Configuration):
        weights: Dict[str, float] = {"a": 1.0}

    assert ModelConfig().dependencies == {}


def test_nested_container_detected_from_the_value(reset_registry):
    """Nesting is caught even when the annotation is permissive."""

    class ModelConfig(Configuration):
        losses: List[Any] = [[CE]]

    with pytest.raises(TypeError, match="Nested containers"):
        ModelConfig().dependencies


def test_key_parses_from_its_string_form_inside_a_container():
    """Members given as strings are validated into keys by pydantic."""

    class ModelConfig(Configuration):
        losses: List[RegistrationKey] = []

    config = ModelConfig(losses=[str(CE)])
    assert config.losses == [CE]
