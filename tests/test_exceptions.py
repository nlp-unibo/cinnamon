"""
Exceptions matrix: exercises every cinnamon custom exception that was not
covered by the existing registry/configuration/modules test suites.

Covers:
    - NotExpandedException
    - NotBoundException
    - AlreadyExpandedException
    - DisconnectedGraphException
"""

import pytest

from cinnamon.configuration import Configuration
from cinnamon.registry import RegistrationKey, Registry
from cinnamon.utility.exceptions import (
    AlreadyExpandedException,
    DisconnectedGraphException,
    NotBoundException,
    NotExpandedException,
    NotRegisteredException,
)

# NotExpandedException


def test_instantiate_unexpanded_raises(reset_registry):
    """
    Trigger NotExpandedException by instantiating a component
     before the registration DAG has been expanded.
    """
    Registry.register_configuration(
        config=Configuration.default(), name="test", namespace="testing"
    )

    with pytest.raises(NotExpandedException):
        Registry.instantiate(name="test", namespace="testing")


# NotBoundException


def test_instantiate_unbound_raises(reset_registry):
    """
    Trigger NotBoundException by instantiating a registered configuration
     that is not bound to any component.
    """
    Registry.register_configuration(
        config=Configuration.default(), name="test", namespace="testing"
    )
    Registry.dag_resolution()

    with pytest.raises(NotBoundException):
        Registry.instantiate(name="test", namespace="testing")


# AlreadyExpandedException


def test_check_graph_after_expansion_raises(reset_registry):
    """
    Trigger AlreadyExpandedException by checking the registration graph
     after it has already been expanded.
    """
    Registry.register_configuration(
        config=Configuration.default(), name="test", namespace="testing"
    )
    Registry.dag_resolution()

    with pytest.raises(AlreadyExpandedException):
        Registry.check_registration_graph()


def test_register_after_expansion_raises(reset_registry):
    """
    Trigger AlreadyExpandedException by registering a new configuration
     after the registration graph has been expanded.
    """
    Registry.register_configuration(
        config=Configuration.default(), name="test", namespace="testing"
    )
    Registry.dag_resolution()

    with pytest.raises(AlreadyExpandedException):
        Registry.register_configuration(
            config=Configuration.default(), name="test", namespace="testing2"
        )


# DisconnectedGraphException


def test_disconnected_graph_raises(reset_registry):
    """
    Trigger DisconnectedGraphException by manually adding an orphan node
     that has no edges to the registration DAG.

    This should never happen via cinnamon APIs and requires manual
     intervention on the dependency DAG.
    """
    Registry._DEPENDENCY_DAG.add_node(
        RegistrationKey(name="orphan", namespace="testing")
    )

    with pytest.raises(DisconnectedGraphException):
        Registry.check_registration_graph()


def test_instantiate_unregistered_raises(reset_registry):
    """
    Trigger NotRegisteredException by instantiating a key that was never
     registered, while the registry is already expanded.
    """
    Registry.register_configuration(
        config=Configuration.default(),
        name="test",
        namespace="testing",
        component="tests.fixtures.EmptyComponent",
    )
    Registry.dag_resolution()

    with pytest.raises(NotRegisteredException):
        Registry.instantiate(name="does_not_exist", namespace="testing")
