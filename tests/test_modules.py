from pathlib import Path

import pytest

from cinnamon.registry import (
    RegistrationContext,
    RegistrationKey,
    Registry,
)
from cinnamon.utility.exceptions import (
    InvalidDirectoryException,
    NamespaceNotFoundException,
)
from cinnamon.utility.registration import NamespaceExtractor
from tests.fixtures import EmptyComponent


def test_parse_configuration_files_with_register():
    """
    Test NamespaceExtractor to retrieve 'external' namespace only from folder path
    """
    extractor = NamespaceExtractor()
    filename = Path(
        ".", "tests", "external_test_repo", "configurations", "test.py"
    ).resolve()
    namespaces = extractor.process(filename=filename)
    assert namespaces == ["external"]


def test_parse_configuration_file_with_register_method():
    """
    Test NamespaceExtractor to retrieve 'external' namespace only from folder
     path when using @register_config
    """
    extractor = NamespaceExtractor()
    filename = Path(
        ".", "tests", "ext_repo_nested", "configurations", "mock.py"
    ).resolve()
    namespaces = extractor.process(filename=filename)
    assert namespaces == ["mock"]


def test_resolve_external_directories_with_dir():
    """
    Resolve external directories provided as path
    """

    external_directories = [Path(".", "tests", "external_test_repo")]
    resolved = Registry.resolve_external_directories(
        external_directories=external_directories
    )
    assert resolved == external_directories


def test_resolve_external_directories_exception():
    """
    Trigger InvalidDirectoryException when providing an invalid external directory
    """

    external_directories = [Path(".", "tests", "fake_repo")]
    with pytest.raises(InvalidDirectoryException):
        Registry.resolve_external_directories(external_directories=external_directories)


def test_load_registrations(reset_registry):
    """
    Load registration from given external directory path and check Registry
    """

    directory = Path(".", "tests", "external_test_repo")
    Registry.load_registrations(directory=directory)
    assert Registry.in_registry(RegistrationKey(name="test", namespace="external"))
    assert Registry.in_registry(RegistrationKey(name="test2", namespace="external"))
    assert not Registry.in_registry(
        RegistrationKey(name="test", namespace="deprecated")
    )


def test_load_registrations_nested_exception(reset_registry):
    """
    Trigger ExternalNamespaceNotFoundException when providing an external
     directory folder that has not been set up
    """

    directory = Path(".", "tests", "ext_repo_nested")
    with pytest.raises(NamespaceNotFoundException):
        Registry.load_registrations(directory=directory)


def test_chained_register_decorator(reset_registry):
    directory = Path(".", "tests", "ext_repo_nested_dec")
    Registry.load_registrations(directory=directory)
    key1 = RegistrationKey(name="config", tags={"nest1"}, namespace="testing")
    key2 = RegistrationKey(name="config", tags={"nest2"}, namespace="testing")
    assert Registry.in_registry(registration_key=key1)
    assert Registry.in_registry(registration_key=key2)

    Registry.dag_resolution()

    c1 = Registry.instantiate(registration_key=key1)
    assert isinstance(c1, EmptyComponent)

    c2 = Registry.instantiate(registration_key=key2)
    assert isinstance(c2, EmptyComponent)


def test_deeply_nested_config(reset_registry):
    directory = Path(".", "tests", "deeply_nested_repo")
    Registry.load_registrations(directory=directory)
    key = RegistrationKey(name="config", namespace="testing")
    assert Registry.in_registry(key)


def test_load_registrations_idempotent(reset_registry):
    """
    Calling load_registrations twice on the same directory must not
     double-register: the second call hits the early-return guard.
    """
    directory = Path(".", "tests", "external_test_repo")
    key = RegistrationKey(name="test", namespace="external")
    key2 = RegistrationKey(name="test2", namespace="external")

    Registry.load_registrations(directory=directory)
    assert Registry.in_registry(key)
    assert Registry.in_registry(key2)

    Registry.load_registrations(directory=directory)
    assert Registry.in_registry(key)
    assert Registry.in_registry(key2)
    # registry was not re-populated / duplicated
    assert len(Registry._REGISTRY) == 2


def test_update_namespaces_duplicate_warns(reset_registry):
    """
    Duplicate namespace across directories raises RuntimeWarning. This is
     currently raised (not warned) inside update_namespaces, so test the raise.
    """
    Registry.update_namespaces(namespaces=["ns1"], module_mapping={"ns1": Path(".")})

    with pytest.raises(RuntimeWarning):
        Registry.update_namespaces(
            namespaces=["ns1"], module_mapping={"ns1": Path(".", "tests")}
        )


def test_load_registrations_module_exec_error(tmp_path, reset_registry):
    """
    A configuration script that fails to execute (e.g. SyntaxError) raises
     RuntimeError wrapping the original failure.
    """
    configs_dir = tmp_path / "configurations"
    configs_dir.mkdir()
    (configs_dir / "bad.py").write_text(
        "def register():\n"
        '    Registry.register_configuration(config=1, name="x", namespace="n"\n'
    )  # unterminated paren => SyntaxError

    with pytest.raises(RuntimeError, match="Failed to execute module"):
        Registry.load_registrations(directory=tmp_path)


# -- NamespaceExtractor --


def _extract(tmp_path, source, name="module.py"):
    path = tmp_path / name
    path.write_text(source)
    return NamespaceExtractor().process(path)


def test_extractor_reads_a_register_method_decorator(tmp_path):
    assert _extract(
        tmp_path,
        """
from cinnamon.registry import register_method

class C:
    @classmethod
    @register_method(name="a", namespace="ns", component="x.Y")
    def default(cls): ...
""",
    ) == ["ns"]


def test_extractor_reads_a_registration_call(tmp_path):
    assert _extract(
        tmp_path,
        """
from cinnamon.registry import Registry, register

@register
def registrations():
    Registry.register_configuration(config=None, name="a", namespace="ns")
""",
    ) == ["ns"]


def test_extractor_resolves_a_module_level_constant(tmp_path):
    """`NAMESPACE = "..."` at the top of the file is the common idiom."""
    assert _extract(
        tmp_path,
        """
from cinnamon.registry import Registry, register

NAMESPACE = "from/constant"

@register
def registrations():
    Registry.register_configuration(config=None, name="a", namespace=NAMESPACE)
""",
    ) == ["from/constant"]


def test_extractor_ignores_other_calls_inside_a_register_function(tmp_path):
    """Regression: any keyword-bearing call was read as a registration.

    A `Param(description=...)` has keywords and no namespace, and indexing the
    empty match list raised IndexError -- taking down the whole build.
    """
    assert _extract(
        tmp_path,
        """
from cinnamon.configuration import Param
from cinnamon.registry import Registry, register

@register
def registrations():
    value = Param(1, description="no namespace here", variants=[2])
    Registry.register_configuration(config=value, name="a", namespace="ns")
""",
    ) == ["ns"]


def test_extractor_does_not_leak_the_register_flag_between_files(tmp_path):
    """Regression: one extractor instance is reused for every file in a build.

    `register_flag` was never reset, so a `@register` function in one module
    made every later module's keyword-bearing calls look like registrations.
    """
    extractor = NamespaceExtractor()

    first = tmp_path / "first.py"
    first.write_text(
        """
from cinnamon.registry import Registry, register

@register
def registrations():
    Registry.register_configuration(config=None, name="a", namespace="ns")
"""
    )
    second = tmp_path / "second.py"
    second.write_text(
        """
from cinnamon.configuration import Param

x = Param(1, description="no register decorator anywhere in this file")
"""
    )

    assert extractor.process(first) == ["ns"]
    assert extractor.process(second) == []


def test_extractor_skips_a_namespace_it_cannot_read_statically(tmp_path):
    """A computed namespace is skipped, not guessed at.

    The previous implementation took the source text after `namespace=` and
    recorded it verbatim, so a computed value became the literal namespace
    `"build_namespace()"`.
    """
    assert (
        _extract(
            tmp_path,
            """
from cinnamon.registry import Registry, register

def build_namespace():
    return "computed"

@register
def registrations():
    Registry.register_configuration(
        config=None, name="a", namespace=build_namespace()
    )
""",
        )
        == []
    )


def test_extractor_handles_async_registration_functions(tmp_path):
    assert _extract(
        tmp_path,
        """
from cinnamon.registry import Registry, register

@register
async def registrations():
    Registry.register_configuration(config=None, name="a", namespace="ns")
""",
    ) == ["ns"]


def test_extractor_reads_an_annotated_constant(tmp_path):
    """`NAMESPACE: str = "..."` binds the same as a bare assignment."""
    assert _extract(
        tmp_path,
        """
from cinnamon.registry import Registry, register

NAMESPACE: str = "annotated"

@register
def registrations():
    Registry.register_configuration(config=None, name="a", namespace=NAMESPACE)
""",
    ) == ["annotated"]


def test_extractor_ignores_unusual_decorator_shapes(tmp_path):
    """A decorator that is neither a Name nor an Attribute is simply not ours."""
    assert (
        _extract(
            tmp_path,
            """
DECORATORS = [lambda f: f]

@DECORATORS[0]
def not_a_registration():
    pass
""",
        )
        == []
    )


def test_extractor_skips_register_method_without_a_readable_namespace(tmp_path):
    """The decorator is recognised; its computed namespace is not guessed at."""
    assert (
        _extract(
            tmp_path,
            """
from cinnamon.registry import register_method

def build():
    return "computed"

class C:
    @classmethod
    @register_method(name="a", namespace=build(), component="x.Y")
    def default(cls): ...
""",
        )
        == []
    )


def test_extractor_reads_a_register_class_decorator(tmp_path):
    """Past a decorator that registers nothing, and on to the one that does."""
    assert _extract(
        tmp_path,
        """
from dataclasses import dataclass

from cinnamon.registry import register_class

NAMESPACE = "decorated"

@dataclass
@register_class(name="a", namespace=NAMESPACE, component="x.Y")
class C: ...
""",
    ) == ["decorated"]


def test_extractor_skips_register_class_without_a_readable_namespace(tmp_path):
    """Recognised as a registration; its computed namespace is not guessed at."""
    assert (
        _extract(
            tmp_path,
            """
from cinnamon.registry import register_class

def build():
    return "computed"

@register_class(name="a", namespace=build(), component="x.Y")
class C: ...
""",
        )
        == []
    )


def test_extractor_ignores_constants_bound_to_something_other_than_a_name(tmp_path):
    """Only `NAME = "..."` binds; an attribute or subscript target is skipped."""
    assert (
        _extract(
            tmp_path,
            """
import types

holder = types.SimpleNamespace()
holder.namespace = "on/an/attribute"
lookup = {}
lookup["namespace"] = "in/a/dict"
""",
        )
        == []
    )


# -- configuration modules that share a namespace and import each other --


def test_namespaces_are_found_in_nested_configuration_folders():
    """``load_registrations`` runs nested scripts, so the scan must reach them.

    A namespace only registered under ``configurations/nested/`` used to be
    missing from the mapping, because the scan globbed one level while the
    loader walked the whole tree.
    """
    directory = Path(".", "tests", "sibling_repo").resolve()
    namespaces, mapping = Registry.parse_configuration_files(directories=[directory])

    assert namespaces == ["sibling"]
    assert mapping == {"sibling": directory}


def test_a_configuration_script_may_import_a_sibling(reset_registry):
    """Importing a sibling buffers its registrations under the importing file.

    The class behind each of those registrations lives in the sibling, so
    looking it up in the importing module's globals raised ``KeyError`` --
    and which of the two files ran first was down to directory order.

    ``inner`` covers the other half of the lookup: a configuration nested
    inside another class is reached by walking its qualified name, not by
    expecting the whole of it to be a module-level name.
    """
    directory = Path(".", "tests", "sibling_repo")
    Registry.load_registrations(directory=directory)

    for name in ("base", "extra", "derived", "deep", "inner"):
        assert Registry.in_registry(RegistrationKey(name=name, namespace="sibling"))


def test_a_class_decorated_repo_is_scanned_and_built(reset_registry):
    """``register_class`` has to be visible to the scan, not only at import.

    ``Registry.build`` reads namespaces out of the source before importing
    anything, and it used to read only the decorators on *methods*. A directory
    whose configurations all sit behind the class decorator therefore scanned as
    registering nothing, and every key pointing into it from another directory
    failed with ``NamespaceNotFoundException`` -- while a build of that
    directory on its own looked fine, because nothing had to cross into it.
    """
    directory = Path(".", "tests", "class_repo").resolve()
    namespaces, mapping = Registry.parse_configuration_files(directories=[directory])

    assert namespaces == ["decorated"]
    assert mapping == {"decorated": directory}

    Registry.build(directory=directory)

    # Registered without a passthrough ``default`` anywhere in the directory,
    # including one nested inside another class.
    assert (
        Registry.retrieve_configuration(
            registration_key=RegistrationKey(name="base", namespace="decorated")
        ).size
        == 1
    )
    assert (
        Registry.retrieve_configuration(
            registration_key=RegistrationKey(
                name="derived", tags={"big"}, namespace="decorated"
            )
        ).size
        == 2
    )
    assert (
        Registry.retrieve_configuration(
            registration_key=RegistrationKey(name="inner", namespace="decorated")
        ).size
        == 4
    )

    # A configuration that writes its own ``default`` keeps it: that method is
    # what the registration builds from, rather than the inherited one.
    assert (
        Registry.retrieve_configuration(
            registration_key=RegistrationKey(name="conditioned", namespace="decorated")
        ).size
        == 3
    )


def test_a_class_decorated_namespace_is_reachable_from_another_directory(
    reset_registry,
):
    """The failure that motivated the scan: a key crossing into that namespace.

    A build of a class-decorated directory on its own looks fine -- nothing has
    to resolve into it, so an empty namespace list costs nothing. It shows up
    the moment another directory refers in, which is what an external
    dependency does.
    """
    Registry.build(
        directory=Path(".", "tests", "class_consumer_repo"),
        external_directories=[Path(".", "tests", "class_repo")],
    )

    assert Registry.in_registry(RegistrationKey(name="config", namespace="consumer"))
    assert Registry.in_registry(RegistrationKey(name="base", namespace="decorated"))


def test_every_script_registers_when_one_pulls_in_another_namespace(reset_registry):
    """A nested load must not close the registration window it ran inside.

    Registering a configuration whose dependency lives in another namespace
    loads that namespace's directory, and that load happens in the middle of
    the outer one. The context was a plain flag, so the nested load cleared it
    on the way out and every script the outer loop had not reached yet ran
    with registration switched off -- registering nothing, raising nothing,
    and leaving which scripts survived down to directory order.
    """
    Registry.build(
        directory=Path(".", "tests", "downstream_repo"),
        external_directories=[Path(".", "tests", "ext_repo_dep")],
    )

    for tag in ("first", "second"):
        assert Registry.in_registry(
            RegistrationKey(name="config", tags={tag}, namespace="downstream")
        )


def test_the_registration_context_counts_its_depth():
    """Leaving a nested block keeps the outer one open."""
    context = RegistrationContext()
    assert context.is_registering is False

    with context:
        with context:
            assert context.is_registering is True
        assert context.is_registering is True
    assert context.is_registering is False

    # An unbalanced exit cannot drive the depth negative, which would leave
    # the next block closed on entry.
    context.__exit__(None, None, None)
    with context:
        assert context.is_registering is True


def test_extractor_follows_an_imported_constant(tmp_path):
    """One `keys.py` for a whole configuration package is the usual layout."""
    package = tmp_path / "project" / "configurations"
    package.mkdir(parents=True)
    (package / "keys.py").write_text('NAMESPACE = "imported"\n')

    assert _extract(
        tmp_path,
        """
from cinnamon.registry import Registry, register

from project.configurations.keys import NAMESPACE

@register
def registrations():
    Registry.register_configuration(config=None, name="a", namespace=NAMESPACE)
""",
        name="importer.py",
    ) == ["imported"]


def test_extractor_follows_a_relative_import_and_a_package_constant(tmp_path):
    """``from .keys import NAMESPACE`` resolves, including through a package."""
    package = tmp_path / "keys"
    package.mkdir()
    (package / "__init__.py").write_text('SHARED = "relative"\n')

    assert _extract(
        tmp_path,
        """
from cinnamon.registry import Registry, register

from .keys import SHARED as NAMESPACE

@register
def registrations():
    Registry.register_configuration(config=None, name="a", namespace=NAMESPACE)
""",
        name="importer.py",
    ) == ["relative"]


def test_extractor_follows_a_re_exported_constant(tmp_path):
    """A constant imported through an intermediate module still resolves."""
    (tmp_path / "keys.py").write_text('NAMESPACE = "re-exported"\n')
    (tmp_path / "middle.py").write_text("from keys import NAMESPACE\n")

    assert _extract(
        tmp_path,
        """
from cinnamon.registry import Registry, register

from middle import NAMESPACE

@register
def registrations():
    Registry.register_configuration(config=None, name="a", namespace=NAMESPACE)
""",
        name="importer.py",
    ) == ["re-exported"]


def test_extractor_gives_up_on_an_import_it_cannot_find(tmp_path):
    """A third-party module is not on disk beside the file importing it."""
    assert (
        _extract(
            tmp_path,
            """
from cinnamon.registry import Registry, register

from somebody_elses_package import NAMESPACE

@register
def registrations():
    Registry.register_configuration(config=None, name="a", namespace=NAMESPACE)
""",
            name="importer.py",
        )
        == []
    )


def test_extractor_ends_the_walk_on_an_import_cycle(tmp_path):
    """Two modules importing the name from each other terminate the walk."""
    (tmp_path / "left.py").write_text("from right import NAMESPACE\n")
    (tmp_path / "right.py").write_text("from left import NAMESPACE\n")

    assert (
        _extract(
            tmp_path,
            """
from cinnamon.registry import Registry, register

from left import NAMESPACE

@register
def registrations():
    Registry.register_configuration(config=None, name="a", namespace=NAMESPACE)
""",
            name="importer.py",
        )
        == []
    )


def test_extractor_gives_up_when_the_imported_module_does_not_define_it(tmp_path):
    """The module is on disk, the name simply is not a constant in it."""
    (tmp_path / "keys.py").write_text('OTHER = "not the one"\n')

    assert (
        _extract(
            tmp_path,
            """
from cinnamon.registry import Registry, register

from keys import NAMESPACE

@register
def registrations():
    Registry.register_configuration(config=None, name="a", namespace=NAMESPACE)
""",
            name="importer.py",
        )
        == []
    )
