"""Static analysis of registration keys: broken references and near-duplicate tags."""

import pytest

from cinnamon.configuration import Configuration, Param
from cinnamon.registry import RegistrationKey, Registry
from cinnamon.utility.exceptions import (
    NamespaceNotFoundException,
    NotRegisteredException,
)
from cinnamon.utility.key_analyzer import (
    Severity,
    analyze_keys,
    explain_variant_tags,
    format_findings,
    format_variant_explanations,
)

NAMESPACE = "nlp"


class Leaf(Configuration):
    x: int = 1


def _register(name, tags=None, namespace=NAMESPACE):
    Registry.register_configuration(
        config=Leaf(), name=name, tags=tags, namespace=namespace
    )


def _categories(findings):
    return [finding.category for finding in findings]


# -- broken references ------------------------------------------------------


def test_every_broken_reference_is_reported_at_once(reset_registry):
    """dag_resolution stops at the first miss; the analyzer reports all of them."""
    _register("tokenizer")
    _register("loader", tags={"imdb"})

    class Pipeline(Configuration):
        tok: RegistrationKey = RegistrationKey(name="tokeniser", namespace=NAMESPACE)
        load: RegistrationKey = RegistrationKey(
            name="loader", tags={"imbd"}, namespace=NAMESPACE
        )

    Registry.register_configuration(
        config=Pipeline(), name="pipeline", namespace=NAMESPACE
    )

    findings = analyze_keys(Registry)
    unresolved = [f for f in findings if f.category == "unresolved-key"]

    assert len(unresolved) == 2
    assert all(finding.severity is Severity.ERROR for finding in unresolved)


def test_broken_reference_carries_a_suggestion_and_a_referrer(reset_registry):
    _register("tokenizer")

    class Pipeline(Configuration):
        tok: RegistrationKey = RegistrationKey(name="tokeniser", namespace=NAMESPACE)

    Registry.register_configuration(
        config=Pipeline(), name="pipeline", namespace=NAMESPACE
    )

    finding = analyze_keys(Registry)[0]

    assert finding.key.name == "tokeniser"
    assert [suggestion.key.name for suggestion in finding.suggestions] == ["tokenizer"]
    assert [key.name for key in finding.referenced_by] == ["pipeline"]


def test_an_empty_namespace_is_called_out(reset_registry):
    """A namespace with no registrations at all is a different mistake."""
    _register("tokenizer")

    class Pipeline(Configuration):
        # same namespace as the parent, so registration does not reject it
        tok: RegistrationKey = RegistrationKey(name="tokenizer", namespace=NAMESPACE)

    Registry.register_configuration(
        config=Pipeline(), name="pipeline", namespace=NAMESPACE
    )
    # reference a namespace nothing registers into
    Registry._DEPENDENCY_DAG.add_edge(
        RegistrationKey(name="pipeline", namespace=NAMESPACE),
        RegistrationKey(name="thing", namespace="ghost"),
        type="child",
    )

    finding = next(f for f in analyze_keys(Registry) if f.key.namespace == "ghost")

    assert "holds no registrations at all" in finding.message


def test_a_resolvable_registry_reports_nothing(reset_registry):
    _register("tokenizer")

    class Pipeline(Configuration):
        tok: RegistrationKey = RegistrationKey(name="tokenizer", namespace=NAMESPACE)

    Registry.register_configuration(
        config=Pipeline(), name="pipeline", namespace=NAMESPACE
    )

    assert analyze_keys(Registry) == []


def test_unresolved_keys_is_empty_after_a_clean_resolution(reset_registry):
    _register("tokenizer")
    Registry.dag_resolution()

    assert Registry.unresolved_keys() == set()


# -- near-duplicate tags ----------------------------------------------------


def test_tags_differing_only_in_case_are_flagged(reset_registry):
    _register("a", tags={"imdb"})
    _register("b", tags={"IMDB"})

    findings = analyze_keys(Registry)

    assert _categories(findings) == ["near-duplicate-tag"]
    assert findings[0].severity is Severity.WARNING
    assert "differ only in case" in findings[0].message


def test_nearly_identical_tags_are_flagged(reset_registry):
    _register("a", tags={"tf-idf"})
    _register("b", tags={"tfidf"})

    assert _categories(analyze_keys(Registry)) == ["near-duplicate-tag"]


def test_unrelated_tags_are_not_flagged(reset_registry):
    _register("a", tags={"imdb"})
    _register("b", tags={"sst2"})

    assert analyze_keys(Registry) == []


def test_generated_variant_tags_are_ignored(reset_registry):
    """Variant expansion mints tags that are near-identical by construction."""
    _register("a", tags={"weight=2.0"})
    _register("b", tags={"weight=3.0"})
    _register("c", tags={"loss.weight=2.0"})

    assert analyze_keys(Registry) == []


# -- report rendering -------------------------------------------------------


def test_format_findings_on_a_clean_registry():
    assert format_findings([]) == "No registration key problems found."


def test_format_findings_renders_every_section(reset_registry):
    _register("tokenizer")
    _register("a", tags={"imdb"})
    _register("b", tags={"IMDB"})

    class Pipeline(Configuration):
        tok: RegistrationKey = RegistrationKey(name="tokeniser", namespace=NAMESPACE)

    Registry.register_configuration(
        config=Pipeline(), name="pipeline", namespace=NAMESPACE
    )

    report = format_findings(analyze_keys(Registry))

    assert "Errors: 1   Warnings: 1" in report
    assert "referenced by:" in report
    assert "did you mean:" in report
    assert "[error] unresolved-key" in report
    assert "[warning] near-duplicate-tag" in report


def test_format_findings_states_when_nothing_is_close(reset_registry):
    _register("tokenizer")

    class Pipeline(Configuration):
        tok: RegistrationKey = RegistrationKey(name="zzzzzzz", namespace=NAMESPACE)

    Registry.register_configuration(
        config=Pipeline(), name="pipeline", namespace=NAMESPACE
    )

    assert "no similar key is registered." in format_findings(analyze_keys(Registry))


# -- enriched exceptions ----------------------------------------------------


def test_not_registered_exception_suggests_the_intended_key(reset_registry):
    _register("loader", tags={"imdb"})
    Registry.expanded = True

    with pytest.raises(NotRegisteredException, match="tag 'imbd' -> 'imdb'"):
        Registry.retrieve_configuration(
            name="loader", tags={"imbd"}, namespace=NAMESPACE
        )


def test_not_registered_exception_without_a_near_match(reset_registry):
    _register("loader", tags={"imdb"})

    with pytest.raises(NotRegisteredException) as raised:
        Registry.retrieve_configuration(name="zzzzzz", namespace="qqq")

    assert "Did you mean" not in str(raised.value)


def test_namespace_exception_suggests_the_intended_namespace(reset_registry):
    Registry._EXP_NAMESPACES.extend(["nlp", "models"])

    class Pipeline(Configuration):
        child: RegistrationKey = RegistrationKey(name="thing", namespace="modles")

    with pytest.raises(NamespaceNotFoundException, match="Did you mean namespace"):
        Registry.register_configuration(
            config=Pipeline(), name="pipeline", namespace=NAMESPACE
        )


def test_namespace_exception_without_a_near_match(reset_registry):
    Registry._EXP_NAMESPACES.extend(["nlp"])

    class Pipeline(Configuration):
        child: RegistrationKey = RegistrationKey(name="thing", namespace="qqqqqqq")

    with pytest.raises(NamespaceNotFoundException) as raised:
        Registry.register_configuration(
            config=Pipeline(), name="pipeline", namespace=NAMESPACE
        )

    assert "Did you mean namespace" not in str(raised.value)


def test_namespace_exception_without_the_missing_namespace():
    """The suggestion argument is optional, so existing callers keep working."""
    message = str(
        NamespaceNotFoundException(
            registration_key=RegistrationKey(name="a", namespace=NAMESPACE),
            namespaces=["nlp"],
        )
    )

    assert "Did you mean namespace" not in message
    assert "Missing namespace: None" in message


# -- indexed variant tags ---------------------------------------------------


class VariedContainerConfig(Configuration):
    losses: list = Param([1], variants=[[1, 2], []])
    label: str = Param("a", variants=["b"])


def test_indexed_variant_tags_are_explained(reset_registry):
    """`losses=variant-1` says nothing about the losses; this says what they are."""
    Registry.register_configuration(
        config=VariedContainerConfig(), name="model", namespace=NAMESPACE
    )
    Registry.dag_resolution()

    explanations = explain_variant_tags(Registry)

    assert explanations == [
        ("model", NAMESPACE, "losses=variant-1", "[1, 2]"),
        ("model", NAMESPACE, "losses=variant-2", "[]"),
    ]


def test_value_derived_tags_need_no_explanation(reset_registry):
    """`label=b` already says what it is, so it is left out."""
    Registry.register_configuration(
        config=VariedContainerConfig(), name="model", namespace=NAMESPACE
    )
    Registry.dag_resolution()

    assert not any("label" in tag for _, _, tag, _ in explain_variant_tags(Registry))


def test_each_tag_is_explained_once(reset_registry):
    """A tag means the same thing on every key that carries it.

    Two varying fields put `losses=variant-1` on several keys; repeating the
    explanation per key would bury it.
    """
    Registry.register_configuration(
        config=VariedContainerConfig(), name="model", namespace=NAMESPACE
    )
    valid_keys, _ = Registry.dag_resolution()

    carriers = [key for key in valid_keys if "losses=variant-1" in key.tags]
    explanations = explain_variant_tags(Registry)

    assert len(carriers) > 1
    assert sum(1 for *_, tag, _ in explanations if tag == "losses=variant-1") == 1


def test_a_registry_without_indexed_variants_explains_nothing(reset_registry):
    _register("plain")
    Registry.dag_resolution()

    assert explain_variant_tags(Registry) == []
    assert format_variant_explanations([]) == ""


def test_dependency_containers_render_by_key_name(reset_registry):
    """Keys render compactly: name, plus tags when it has them."""

    class ModelConfig(Configuration):
        children: list = Param(
            [RegistrationKey(name="a", namespace=NAMESPACE)],
            variants=[
                [
                    RegistrationKey(name="a", namespace=NAMESPACE),
                    RegistrationKey(name="b", tags={"t"}, namespace=NAMESPACE),
                ]
            ],
        )

    _register("a")
    _register("b", tags={"t"})
    Registry.register_configuration(
        config=ModelConfig(), name="model", namespace=NAMESPACE
    )
    Registry.dag_resolution()

    assert explain_variant_tags(Registry) == [
        ("model", NAMESPACE, "children=variant-1", "[a, b[t]]")
    ]


def test_a_long_value_is_truncated(reset_registry):
    # A str variant is taggable and renders into the tag itself, so it never
    # produces an indexed tag. It takes a container to get one.
    class ModelConfig(Configuration):
        blob: list = Param([0], variants=[list(range(100))])

    Registry.register_configuration(
        config=ModelConfig(), name="model", namespace=NAMESPACE
    )
    Registry.dag_resolution()

    rendering = explain_variant_tags(Registry)[0][3]
    assert rendering.endswith("...")
    assert len(rendering) == 60


def test_format_variant_explanations_groups_by_configuration():
    rendered = format_variant_explanations(
        [
            ("model", "nlp", "losses=variant-1", "[ce]"),
            ("model", "nlp", "metrics=variant-1", "{acc: acc}"),
            ("other", "nlp", "x=variant-1", "[1]"),
        ]
    )

    assert rendered.count("model (ns=nlp)") == 1
    assert "other (ns=nlp)" in rendered
    # tags are padded to a common width, so match on content not spacing
    assert "losses=variant-1" in rendered and "= [ce]" in rendered


def test_a_dict_variant_renders_its_labels(reset_registry):
    class ModelConfig(Configuration):
        metrics: dict = Param({"acc": 1}, variants=[{"acc": 1, "f1": 2}])

    Registry.register_configuration(
        config=ModelConfig(), name="model", namespace=NAMESPACE
    )
    Registry.dag_resolution()

    assert explain_variant_tags(Registry) == [
        ("model", NAMESPACE, "metrics=variant-1", "{acc: 1, f1: 2}")
    ]


def test_explanations_skip_keys_without_a_configuration(reset_registry):
    """A registry entry may carry no configuration; it explains nothing."""
    Registry.register_configuration(
        config=VariedContainerConfig(), name="model", namespace=NAMESPACE
    )
    Registry.dag_resolution()
    for key in list(Registry._REGISTRY):
        Registry._REGISTRY[key].config = None

    assert explain_variant_tags(Registry) == []


def test_a_tag_naming_no_field_is_ignored(reset_registry):
    """Hand-written tags can look like variant tags without being one."""
    Registry.register_configuration(
        config=VariedContainerConfig(),
        name="model",
        tags={"handwritten=variant-9"},
        namespace=NAMESPACE,
    )
    Registry.dag_resolution()

    assert not any(
        tag == "handwritten=variant-9" for *_, tag, _ in explain_variant_tags(Registry)
    )
