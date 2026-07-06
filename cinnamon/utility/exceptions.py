import os
from dataclasses import dataclass
from pathlib import Path
from typing import AnyStr, List, Optional, Union

__all__ = [
    "AlreadyRegisteredException",
    "NamespaceNotFoundException",
    "NotRegisteredException",
    "NotBoundException",
    "DisconnectedGraphException",
    "NotADAGException",
    "AlreadyExpandedException",
    "NotExpandedException",
    "InvalidDirectoryException",
    "ValidationResult",
    "ValidationFailureException",
]


class AlreadyRegisteredException(Exception):
    def __init__(self, registration_key: "cinnamon.registry.RegistrationKey"):  # noqa: F821
        super(AlreadyRegisteredException, self).__init__(
            f"A configuration has already been registered with the same key!"
            f"Got: {registration_key}"
        )


class NamespaceNotFoundException(Exception):
    def __init__(
        self,
        registration_key: "cinnamon.registry.RegistrationKey",  # noqa: F821
        namespaces: List[str],
    ):
        super(NamespaceNotFoundException, self).__init__(
            f"The registration key namespace cannot be found. {os.linesep}"
            f"Key: {registration_key}{os.linesep}"
            f"Namespaces: {namespaces}{os.linesep}"
            f"Please, make sure you add the main directory containing that namespace "
            f"when calling Registry.setup() method"
        )


class NotRegisteredException(Exception):
    def __init__(self, registration_key: "cinnamon.registry.RegistrationKey"):  # noqa: F821
        super(NotRegisteredException, self).__init__(
            f"Could not find key {registration_key}. Did you register it?"
        )


class NotBoundException(Exception):
    def __init__(self, registration_key: "cinnamon.registry.RegistrationKey"):  # noqa: F821
        super(NotBoundException, self).__init__(
            f"Registered configuration {registration_key} is not bound to a component."
            f" Did you bind it?"
        )


class DisconnectedGraphException(Exception):
    def __init__(self, nodes):
        super().__init__(f"Disconnected graph! Nodes {nodes} are not connected!")


class NotADAGException(Exception):
    def __init__(self, edges):
        super().__init__(
            f"The built graph is not a DAG! {os.linesep}"
            f"Please find below the edge list: {os.linesep}"
            f"{self.build_edge_view(edges)}"
        )

    def build_edge_view(self, edges):
        view = []
        for edge in edges:
            node_view = f"{edge[0]} -> {edge[1]}"
            view.append(node_view)
        return os.linesep.join(view)


class AlreadyExpandedException(Exception):
    def __init__(self):
        super().__init__(
            "The registration graph has already been expanded!"
            " No further registrations are allowed."
        )


class NotExpandedException(Exception):
    def __init__(self):
        super().__init__(
            "The registration graph has yet to be expanded!"
            " Configuration retrieval is not allowed."
        )


class InvalidDirectoryException(Exception):
    def __init__(self, directory: Union[AnyStr, Path]):
        super().__init__(
            f"The directory path does not exist or is not a directory. {os.linesep}"
            f"Path: {directory}"
        )


@dataclass
class ValidationResult:
    """
    Stores conditions evaluation result (see ``Configuration.validate()``).

    Args:
        passed: True if all conditions are True
        error_message: describes which condition failed during the evaluation process.
    """

    passed: bool
    source: str
    error_message: Optional[str] = None

    @property
    def stack_trace(self):
        return f"""
            Source: {self.source}.
            Message: {self.error_message}
        """


class ValidationFailureException(Exception):
    def __init__(self, validation_result: ValidationResult):
        super().__init__(
            f"Source: {validation_result.source}{os.linesep}"
            f"The validation process has failed!{os.linesep}"
            f"Passed: {validation_result.passed}{os.linesep}"
            f"Error message: {validation_result.error_message}"
        )
