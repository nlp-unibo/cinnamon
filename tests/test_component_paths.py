"""
Resolving component paths without importing them, and the lightweight-field rule.

Both exist to keep the component/configuration boundary cheap to respect: a
component path is checked on the filesystem rather than by importing whatever it
names, and a configuration that tries to *hold* a component is told why not.
"""

import sys

import pytest
from pydantic import ConfigDict

from cinnamon.configuration import Configuration
from cinnamon.registry import Registry
from cinnamon.utility.exceptions import UnsupportedFieldTypeException
from cinnamon.utility.registration import import_class_from_string, locate_module
from cinnamon.utility.static_analyzer import _check_component_path, analyze_registry

NAMESPACE = "paths"


class Outer:
    """Host for a nested component, which splits differently from a flat one."""

    class Inner:
        def __init__(self, x: int = 1):
            self.x = x


class Simple:
    def __init__(self, x: int = 1):
        self.x = x


class Leaf(Configuration):
    x: int = 1


# -- locating modules without importing -------------------------------------


def test_locate_module_finds_a_package_without_importing_it():
    """The point of the exercise: no module code runs."""
    sys.modules.pop("html.parser", None)

    origin, missing = locate_module("html.parser")

    assert origin is not None and origin.endswith("parser.py")
    assert missing is None
    assert "html.parser" not in sys.modules


def test_locate_module_reports_the_first_missing_segment():
    assert locate_module("json.no_such_module")[1] == "json.no_such_module"
    assert locate_module("no_such_package.anything")[1] == "no_such_package"


def test_locate_module_stops_descending_into_a_plain_module():
    """A module is not a package, so nothing can be nested below it."""
    assert locate_module("json.encoder.deeper")[1] == "json.encoder.deeper"


# -- importing, including nested classes ------------------------------------


def test_import_class_from_string_handles_a_flat_path():
    assert import_class_from_string(f"{__name__}.Simple") is Simple


def test_import_class_from_string_handles_a_nested_class():
    """Regression: splitting once treated 'Outer' as part of the module path."""
    assert import_class_from_string(f"{__name__}.Outer.Inner") is Outer.Inner


def test_import_class_from_string_still_raises_for_a_missing_module():
    with pytest.raises(ImportError):
        import_class_from_string("no_such_package.thing.Klass")


def test_import_class_from_string_still_raises_for_a_missing_attribute():
    with pytest.raises(AttributeError):
        import_class_from_string(f"{__name__}.NoSuchClass")


# -- the shallow path check -------------------------------------------------


def test_shallow_check_accepts_a_resolvable_path():
    assert _check_component_path("json.encoder.JSONEncoder") == ([], [])


def test_shallow_check_errors_on_an_unknown_top_level_package():
    errors, warnings = _check_component_path("no_such_package.models.Thing")

    assert warnings == []
    assert "no module or package named 'no_such_package'" in errors[0]


def test_shallow_check_errors_on_a_path_with_no_dots():
    errors, _ = _check_component_path("Bare")

    assert "is not a dotted path" in errors[0]


def test_shallow_check_warns_when_it_cannot_tell_typo_from_nested_class():
    """A wrong module and a nested class are indistinguishable on disk."""
    for path in ("json.no_such_module.Thing", "json.encoder.JSONEncoder.Inner"):
        errors, warnings = _check_component_path(path)

        assert errors == []
        assert "is not a module" in warnings[0]


def test_shallow_check_never_imports_the_component():
    sys.modules.pop("html.parser", None)

    _check_component_path("html.parser.HTMLParser")

    assert "html.parser" not in sys.modules


# -- analyze_registry(deep=...) ---------------------------------------------


def _register(name, component):
    Registry.register_configuration(
        config=Leaf(), name=name, namespace=NAMESPACE, component=component
    )


def test_shallow_analysis_flags_a_bad_path(reset_registry):
    _register("good", "json.encoder.JSONEncoder")
    _register("bad", "no_such_package.Thing")
    Registry.dag_resolution()

    results = analyze_registry(Registry, deep=False)
    failed = {name for (name, _, _), (ok, _, _) in results.items() if not ok}

    assert failed == {"bad"}


def test_shallow_analysis_skips_signature_checking(reset_registry):
    """A field the component cannot accept is a deep-only finding."""
    Registry.register_configuration(
        config=Leaf(),  # declares `x`; Simple accepts `x`, so add a stray field
        name="mismatch",
        namespace=NAMESPACE,
        component=f"{__name__}.NoArgs",
    )
    Registry.dag_resolution()

    shallow = analyze_registry(Registry, deep=False)
    deep = analyze_registry(Registry, deep=True)

    assert all(ok for ok, _, _ in shallow.values())
    assert not all(ok for ok, _, _ in deep.values())


class NoArgs:
    def __init__(self):
        pass


# -- the lightweight-field rule ---------------------------------------------


class Heavy:
    """Stands in for an sklearn estimator or a torch module."""

    def __init__(self, weights=None):
        self.weights = weights


def test_a_component_typed_field_is_refused_with_cinnamon_s_reasoning():
    with pytest.raises(UnsupportedFieldTypeException) as raised:

        class Leaky(Configuration):
            alpha: float = 1.0
            model: Heavy = Heavy()

    message = str(raised.value)
    assert "Field 'model'" in message
    assert "Leaky" in message
    # the point of intercepting at all: say why, not just what
    assert "they do not hold it" in message
    assert "RegistrationKey" in message


def test_the_escape_hatch_is_still_available():
    """Explained, not policed: a user who means it can still opt in."""

    class Opted(Configuration):
        model_config = ConfigDict(arbitrary_types_allowed=True)
        model: Heavy = Heavy()

    assert isinstance(Opted().model, Heavy)


def test_ordinary_configurations_are_unaffected():
    class Fine(Configuration):
        alpha: float = 1.0
        label: str = "x"

    assert Fine().model_dump() == {"alpha": 1.0, "label": "x"}


# -- the interception machinery itself --------------------------------------


def test_field_name_is_recovered_from_eager_annotations():
    """Pre-3.14 namespaces expose __annotations__ directly."""
    from cinnamon.configuration import _class_body_annotations, _offending_field

    namespace = {"__annotations__": {"model": Heavy, "alpha": float}}

    assert _class_body_annotations(namespace) == {"model": Heavy, "alpha": float}
    assert _offending_field(namespace, f"{__name__}.Heavy") == "model"


def test_field_name_is_recovered_from_a_string_annotation():
    """`from __future__ import annotations` leaves the annotation as text."""
    from cinnamon.configuration import _offending_field

    namespace = {"__annotations__": {"model": "Heavy"}}

    assert _offending_field(namespace, f"{__name__}.Heavy") == "model"


def test_field_name_lookup_gives_up_quietly():
    from cinnamon.configuration import _class_body_annotations, _offending_field

    assert _offending_field({}, None) is None
    assert _offending_field({"__annotations__": {"a": int}}, "pkg.Other") is None
    assert _class_body_annotations({}) == {}


def test_annotations_are_read_through_the_pep_649_hook():
    from cinnamon.configuration import _class_body_annotations

    assert _class_body_annotations({"__annotate_func__": lambda fmt: {"a": int}}) == {
        "a": int
    }


def test_other_schema_errors_are_left_to_pydantic(monkeypatch):
    """Only the 'unknown type' code is intercepted.

    Pydantic's messages for every other schema problem are good, and replacing
    them with a lecture about configuration weight would be wrong.
    """
    from pydantic import PydanticSchemaGenerationError

    from cinnamon.configuration import _ModelMetaclass

    unrelated = PydanticSchemaGenerationError("something else entirely")
    unrelated.code = "some-other-code"

    def boom(*args, **kwargs):
        raise unrelated

    monkeypatch.setattr(_ModelMetaclass, "__new__", boom)

    with pytest.raises(PydanticSchemaGenerationError) as raised:

        class Passthrough(Configuration):
            x: int = 1

    assert raised.value is unrelated


def test_namespace_packages_resolve(tmp_path, monkeypatch):
    """A directory with no __init__.py is a package, and must not read as missing.

    Regression: `locate_module` returns ``(None, None)`` for a namespace package
    -- found, but with no file of its own -- and the path check treated the
    absent origin as an absent module. Every component under `examples/`, which
    has no `__init__.py`, was reported as unresolvable.
    """
    (tmp_path / "nspkg" / "inner").mkdir(parents=True)
    (tmp_path / "nspkg" / "inner" / "mod.py").write_text("class Thing:\n    pass\n")
    monkeypatch.syspath_prepend(str(tmp_path))

    origin, missing = locate_module("nspkg")
    assert (origin, missing) == (None, None)  # found, no file

    assert _check_component_path("nspkg.inner.mod.Thing") == ([], [])
