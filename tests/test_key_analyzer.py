"""Static analysis of registration keys: broken references and near-duplicate tags."""

import pytest

from cinnamon.configuration import Configuration
from cinnamon.registry import RegistrationKey, Registry
from cinnamon.utility.exceptions import (
    NamespaceNotFoundException,
    NotRegisteredException,
)
from cinnamon.utility.key_analyzer import (
    Severity,
    analyze_keys,
    format_findings,
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
