"""
Registering by a key declared once, rather than by its name, tags and namespace.

A project that keeps its keys in one module used to write each key twice: as a
constant other configurations refer to, and again, field by field, in the
decorator that registers it. Nothing compared the two, so a typo in either left
a key that nothing registered, found only when something asked for it.
"""

from pathlib import Path

import pytest

from cinnamon.configuration import Configuration
from cinnamon.registry import (
    Namespace,
    RegistrationKey,
    Registry,
    register_class,
    register_method,
)
from tests.key_repo.configurations.keys import BASE, CALLED, DERIVED, METHOD
from tests.test_modules import _extract

KEY_REPO = Path(".", "tests", "key_repo")


def test_a_namespace_builds_its_keys():
    namespace = Namespace("ns")

    assert namespace == "ns"
    assert namespace.key("model", "fr", "gru") == RegistrationKey(
        name="model", tags={"fr", "gru"}, namespace="ns"
    )
    assert namespace.key("model") == RegistrationKey(name="model", namespace="ns")


def test_a_key_repo_is_scanned_and_built(reset_registry):
    """No registration names its namespace, yet the scan finds every one."""
    directory = KEY_REPO.resolve()
    namespaces, mapping = Registry.parse_configuration_files(directories=[directory])

    assert set(namespaces) == {"keyed"}
    assert mapping == {"keyed": directory}

    Registry.build(directory=directory)

    for key, size in ((BASE, 1), (DERIVED, 2), (METHOD, 3), (CALLED, 4)):
        assert Registry.retrieve_configuration(registration_key=key).size == size
    assert Registry.retrieve_configuration(registration_key=DERIVED).child == BASE


@pytest.mark.parametrize("decorator", [register_class, register_method])
@pytest.mark.parametrize(
    "restated",
    [{"name": "a"}, {"namespace": "ns"}, {"tags": {"t"}}],
    ids=["name", "namespace", "tags"],
)
def test_a_key_cannot_be_restated(decorator, restated):
    with pytest.raises(TypeError, match="registered by its key"):
        decorator(key=RegistrationKey(name="a", namespace="ns"), **restated)


@pytest.mark.parametrize("decorator", [register_class, register_method])
@pytest.mark.parametrize(
    "partial", [{}, {"name": "a"}, {"namespace": "ns"}], ids=["none", "name", "ns"]
)
def test_a_registration_needs_a_key_or_a_name_and_a_namespace(decorator, partial):
    with pytest.raises(TypeError, match="needs a key"):
        decorator(**partial)


def test_the_explicit_form_still_registers(reset_registry):
    @register_class(name="a", namespace="ns", tags={"t"})
    class Explicit(Configuration): ...

    assert Explicit.__name__ == "Explicit"


# -- NamespaceExtractor --


def test_extractor_reads_a_namespace_constant_in_the_explicit_form(tmp_path):
    assert _extract(
        tmp_path,
        """
from cinnamon.registry import Namespace, register_class

NAMESPACE = Namespace("wrapped")

@register_class(name="a", namespace=NAMESPACE)
class C: ...
""",
    ) == ["wrapped"]


def test_extractor_follows_a_key_declared_in_the_same_file(tmp_path):
    assert _extract(
        tmp_path,
        """
from cinnamon.registry import Namespace, register_method

NAMESPACE = Namespace("local")
A = NAMESPACE.key("a")

class C:
    @classmethod
    @register_method(key=A)
    def default(cls): ...
""",
    ) == ["local"]


def test_extractor_follows_an_imported_key_to_an_imported_namespace(tmp_path):
    """The usual layout: keys in one module, the namespace in another."""
    package = tmp_path / "project"
    package.mkdir()
    (package / "base.py").write_text(
        'from cinnamon.registry import Namespace\nNAMESPACE = Namespace("deep")\n'
    )
    (package / "keys.py").write_text(
        "from project.base import NAMESPACE\nA = NAMESPACE.key('a', 't')\n"
    )

    assert _extract(
        tmp_path,
        """
from cinnamon.registry import register_class

from project.keys import A

@register_class(key=A)
class C: ...
""",
    ) == ["deep"]


def test_extractor_reads_a_registration_key_call(tmp_path):
    """Both in place and bound to a name, with a literal or constant namespace."""
    assert _extract(
        tmp_path,
        """
from cinnamon.registry import RegistrationKey, Registry, register, register_class

NAMESPACE = "constant"
A = RegistrationKey(name="a", namespace=NAMESPACE)

@register_class(key=A)
class C: ...

@register_class(key=RegistrationKey(name="b", namespace="inline"))
class D: ...

@register
def registrations():
    Registry.register_configuration(config=None, key=A)
""",
    ) == ["constant", "inline", "constant"]


@pytest.mark.parametrize(
    "key",
    [
        "UNKNOWN",
        "NOT_A_CALL",
        "build()",
        "RegistrationKey(name='a')",
        "RegistrationKey(name='a', namespace=compute())",
        "NAMESPACE.key",
        "NUMBER_NAMESPACE.key('a')",
        "holder.namespace.key('a')",
        "MISSING_NAMESPACE.key('a')",
    ],
)
def test_extractor_skips_a_key_it_cannot_read_statically(tmp_path, key):
    """A key whose namespace needs running code is skipped, not guessed at."""
    assert (
        _extract(
            tmp_path,
            f"""
from cinnamon.registry import Namespace, RegistrationKey, register_class

NOT_A_CALL = "a string, not a key"
NUMBER_NAMESPACE = Namespace(1)
NAMESPACE = Namespace("ns")

@register_class(key={key})
class C: ...
""",
        )
        == []
    )


def test_extractor_skips_an_imported_key_it_cannot_find(tmp_path):
    assert (
        _extract(
            tmp_path,
            """
from cinnamon.registry import register_class

from nowhere.keys import A

@register_class(key=A)
class C: ...
""",
        )
        == []
    )


def test_extractor_ignores_a_key_outside_a_registration_function(tmp_path):
    assert (
        _extract(
            tmp_path,
            """
from cinnamon.registry import Registry

Registry.register_configuration(config=None, key=None)
""",
        )
        == []
    )


def test_extractor_skips_a_registration_without_namespace_or_key(tmp_path):
    """Such a decorator raises at import; the scan records nothing for it."""
    assert (
        _extract(
            tmp_path,
            """
from cinnamon.registry import register_class

@register_class(component="x.Y")
class C: ...
""",
        )
        == []
    )


def test_a_registered_key_keeps_its_description(reset_registry):
    """The stored key is a copy: registration marks it, not the declared constant."""
    Registry.build(directory=KEY_REPO.resolve())

    (stored,) = Registry.retrieve_runnable_keys()
    assert stored == BASE
    assert stored.description == "the smallest configuration"
    assert "__runnable" not in BASE.special_tags


def test_an_ad_hoc_registration_copies_its_key(reset_registry):
    """The ad-hoc path copies the key, as the decorators do."""
    key = Namespace("ns").key("a", description="kept")

    stored = Registry.register_configuration(
        config=Configuration.default(), key=key, run_method="run"
    )

    assert stored == key
    assert stored.description == "kept"
    assert "__runnable" in stored.special_tags
    assert "__runnable" not in key.special_tags


def test_an_ad_hoc_registration_takes_a_key_or_its_fields(reset_registry):
    key = RegistrationKey(name="a", namespace="ns")

    with pytest.raises(TypeError, match="registered by its key"):
        Registry.register_configuration(
            config=Configuration.default(), key=key, name="a"
        )
    with pytest.raises(TypeError, match="needs a key"):
        Registry.register_configuration(config=Configuration.default(), name="a")
