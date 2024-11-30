from pathlib import Path

import pytest

from cinnamon_core.registry import (
    Registry,
    InvalidDirectoryException,
    RegistrationKey,
    NamespaceNotFoundException
)
from cinnamon_core.utility.registration import NamespaceExtractor
from tests.fixtures import reset_registry


def test_parse_configuration_files():
    """
    Test NamespaceExtractor to retrieve 'external' namespace only from folder path
    """
    extractor = NamespaceExtractor()
    filename = Path('.', 'external_test_repo', 'configurations', 'test.py').resolve()
    namespaces = extractor.process(filename=filename)
    assert namespaces == ['external']


def test_resolve_external_directories_with_dir():
    """
    Resolve external directories provided as path
    """

    external_directories = [
        Path('.', 'external_test_repo')
    ]
    resolved = Registry.resolve_external_directories(external_directories=external_directories,
                                                     save_directory=Path('.'))
    assert resolved == external_directories


def test_resolve_external_directories_exception():
    """
    Trigger InvalidDirectoryException when providing an invalid external directory
    """

    external_directories = [
        Path('.', 'fake_repo')
    ]
    with pytest.raises(InvalidDirectoryException):
        Registry.resolve_external_directories(external_directories=external_directories,
                                              save_directory=Path('.'))


def test_load_registrations(
        reset_registry
):
    """
    Load registration from given external directory path and check Registry
    """

    directory = Path('.', 'external_test_repo')
    Registry.load_registrations(directory=directory)
    assert Registry.in_registry(RegistrationKey(name='test', namespace='external'))
    assert Registry.in_registry(RegistrationKey(name='test2', namespace='external'))
    assert not Registry.in_registry(RegistrationKey(name='test', namespace='deprecated'))


def test_load_registrations_nested_exception(
        reset_registry
):
    """
    Trigger ExternalNamespaceNotFoundException when providing an external directory folder that has not been set up
    """

    directory = Path('.', 'ext_repo_nested')
    with pytest.raises(NamespaceNotFoundException):
        Registry.load_registrations(directory=directory)
