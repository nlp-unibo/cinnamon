from pathlib import Path

import pytest

from cinnamon.registry import (
    RegistrationKey,
    Registry,
)
from cinnamon.utility.exceptions import (
    InvalidDirectoryException,
    NamespaceNotFoundException,
)
from cinnamon.utility.registration import NamespaceExtractor
from tests.fixtures import EmptyComponent, reset_registry


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
    """Test test chained register decorator."""
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
    """Test test deeply nested config."""
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
