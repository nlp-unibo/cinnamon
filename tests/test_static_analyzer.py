from pathlib import Path
from collections import deque

import pytest

from cinnamon.configuration import Configuration
from cinnamon.registry import Registry
from cinnamon.utility.static_analyzer import (
    _check_signature,
    _get_component_signature,
    analyze_registry,
    print_analysis_summary,
    quick_validate,
)
from tests.fixtures import BaseConfig, reset_registry


class NoArgsComponent:
    """Explicit __init__ on purpose: does NOT inherit object.__init__'s **kwargs."""

    def __init__(self):
        pass


class VarKwargsComponent:
    def __init__(self, mandatory: int, **kwargs):
        self.mandatory = mandatory
        self.kwargs = kwargs


class VarArgsComponent:
    def __init__(self, *args):
        self.args = args


class VarKwargsConfig(Configuration):
    mandatory: int = 1
    another: int = 2


class UninspectableComponent:
    """__init__ is a builtin; inspect.signature raises ValueError."""

    __init__ = deque.append


# `_get_component_signature`


def test_signature_required_and_params():
    """Test test signature required and params."""
    sig = _get_component_signature("tests.fixtures.BaseComponent")
    assert sig.params == frozenset({"x", "y"})
    assert sig.required == frozenset({"x", "y"})
    assert not sig.accepts_var_args and not sig.accepts_var_kwargs


def test_signature_no_args_component():
    """Test test signature no args component."""
    sig = _get_component_signature(__name__ + ".NoArgsComponent")
    assert sig.params == frozenset()
    assert sig.required == frozenset()
    assert not sig.accepts_var_args and not sig.accepts_var_kwargs


def test_signature_var_kwargs():
    """Test test signature var kwargs."""
    sig = _get_component_signature(__name__ + ".VarKwargsComponent")
    assert sig.accepts_var_kwargs
    assert not sig.accepts_var_args
    assert sig.required == frozenset({"mandatory"})


def test_signature_var_args():
    """Test test signature var args."""
    sig = _get_component_signature(__name__ + ".VarArgsComponent")
    assert sig.accepts_var_args
    assert not sig.accepts_var_kwargs
    assert sig.required == frozenset()


def test_signature_is_cached():
    """Test test signature is cached."""
    sig = _get_component_signature("tests.fixtures.BaseComponent")
    assert _get_component_signature("tests.fixtures.BaseComponent") is sig


def test_signature_unknown_component_raises():
    """Test test signature unknown component raises."""
    with pytest.raises(RuntimeError):
        _get_component_signature("tests.fixtures.NoSuchComponent")


def test_signature_uninspectable_component_raises():
    """inspect.signature failure on a builtin __init__ is reported as RuntimeError."""
    with pytest.raises(RuntimeError, match="Cannot inspect __init__"):
        _get_component_signature(__name__ + ".UninspectableComponent")


# `_check_signature`


def test_check_signature_matching_config():
    """Test test check signature matching config."""
    assert _check_signature("tests.fixtures.BaseComponent", BaseConfig.default()) == []


def test_check_signature_missing_required():
    """Test test check signature missing required."""
    problems = _check_signature(
        "tests.fixtures.BaseComponent", Configuration.default()
    )
    assert len(problems) == 1
    assert "requires parameters" in problems[0]
    assert "x" in problems[0] and "y" in problems[0]


def test_check_signature_extra_fields():
    """Test test check signature extra fields."""
    problems = _check_signature(
        __name__ + ".NoArgsComponent", BaseConfig.default()
    )
    assert len(problems) == 1
    assert "does not accept" in problems[0]
    assert "x" in problems[0] and "y" in problems[0]


def test_check_signature_var_kwargs_allows_extra():
    """Test test check signature var kwargs allows extra."""
    assert (
        _check_signature(__name__ + ".VarKwargsComponent", VarKwargsConfig())
        == []
    )


def test_check_signature_import_error_reported_as_problem():
    """Test test check signature import error reported as problem."""
    problems = _check_signature(
        "tests.fixtures.NoSuchComponent", Configuration.default()
    )
    assert len(problems) == 1
    assert "cannot be imported" in problems[0]


# `analyze_registry`


def _build_default_registry():
    Registry.register_configuration(
        config=Configuration.default(),
        name="valid",
        namespace="analyzer",
        component=__name__ + ".NoArgsComponent",
    )
    Registry.register_configuration(
        config=BaseConfig.default(),
        name="mismatch",
        namespace="analyzer",
        component=__name__ + ".NoArgsComponent",
    )
    Registry.register_configuration(
        config=BaseConfig.default(),
        name="unbound",
        namespace="analyzer",
    )
    Registry.dag_resolution()


def test_analyze_registry_states(reset_registry):
    """Test test analyze registry states."""
    _build_default_registry()
    results = analyze_registry()

    valid, _, _ = results[("valid", "analyzer", frozenset())]
    assert valid is True

    mismatch_ok, errs, warns = results[("mismatch", "analyzer", frozenset())]
    assert mismatch_ok is False
    assert warns == []
    assert any("does not accept" in e for e in errs)

    unbound_ok, unbound_errs, unbound_warns = results[
        ("unbound", "analyzer", frozenset())
    ]
    assert unbound_ok is True  # unbound is a warning, not an error
    assert unbound_errs == []
    assert len(unbound_warns) == 1
    assert "not bound" in unbound_warns[0]


def test_analyze_registry_rejects_unexpanded(reset_registry):
    """Test test analyze registry rejects unexpanded."""
    Registry.register_configuration(
        config=Configuration.default(),
        name="valid",
        namespace="analyzer",
        component=__name__ + ".NoArgsComponent",
    )
    with pytest.raises(RuntimeError, match="must be expanded"):
        analyze_registry()


def test_analyze_registry_raise_on_error(reset_registry):
    """Test test analyze registry raise on error."""
    _build_default_registry()
    with pytest.raises(RuntimeError, match="Binding error"):
        analyze_registry(raise_on_error=True)


def test_analyze_registry_skips_none_configs(reset_registry):
    """
    Registrations whose stored ConfigurationInfo.config is None are skipped,
     not analyzed.
    """
    Registry.register_configuration(
        config=Configuration.default(), name="real", namespace="analyzer"
    )
    # simulate a stored entry with no config object
    from cinnamon.registry import ConfigurationInfo, RegistrationKey as RK

    stub_key = RK(name="ghost", namespace="analyzer")
    Registry._REGISTRY[stub_key] = ConfigurationInfo(config=None)
    Registry.dag_resolution()

    results = analyze_registry()

    assert ("real", "analyzer", frozenset()) in results
    assert ("ghost", "analyzer", frozenset()) not in results


def test_analysis_summary_all_clean(reset_registry, capsys):
    """A fully clean analysis (no errors, no warnings) prints the success line."""
    Registry.register_configuration(
        config=Configuration.default(),
        name="clean",
        namespace="analyzer",
        component=__name__ + ".NoArgsComponent",
    )
    Registry.dag_resolution()

    print_analysis_summary(analyze_registry())
    out = capsys.readouterr().out

    assert "All bindings are valid!" in out


def test_print_analysis_summary_smoke(reset_registry, capsys):
    """Test test print analysis summary smoke."""
    _build_default_registry()
    print_analysis_summary(analyze_registry())
    out = capsys.readouterr().out
    assert "Static Analyzer Summary" in out
    assert "Total registered configurations: 3" in out
    assert "Binding problems: 1" in out
    assert "not bound" in out  # warnings survive even with errors present


def test_print_analysis_summary_warns_without_errors(reset_registry, capsys):
    """All-ok registry still reports unbound warnings (regression: early return)."""
    Registry.register_configuration(
        config=BaseConfig.default(), name="unbound", namespace="analyzer"
    )
    Registry.dag_resolution()
    print_analysis_summary(analyze_registry())
    out = capsys.readouterr().out
    assert "All bindings are valid!" not in out
    assert "not bound" in out


# `quick_validate` (end-to-end)


def test_quick_validate_external_test_repo():
    """Build+analyze a real repo: both bound external configs are valid."""
    results = quick_validate(Path(".", "tests", "external_test_repo"))
    assert results
    assert all(ok for ok, _, _ in results.values())
    # namespaces show up as keys
    assert ("test2", "external", frozenset()) in results


def test_quick_validate_nonexistent_directory():
    """Test test quick validate nonexistent directory."""
    from cinnamon.utility.exceptions import InvalidDirectoryException

    with pytest.raises(InvalidDirectoryException):
        quick_validate(Path(".", "tests", "no_such_dir"))