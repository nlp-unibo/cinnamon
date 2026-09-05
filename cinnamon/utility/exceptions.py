from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional, Union

if TYPE_CHECKING:
    from cinnamon.registry import RegistrationKey
    from cinnamon.utility.suggestions import KeySuggestion


def _suggestion_block(suggestions: "List[KeySuggestion] | None") -> str:
    """Render "did you mean" lines, or nothing when there is no near match."""
    if not suggestions:
        return ""
    lines = [f"{os.linesep}Did you mean:"]
    lines += [
        f"  - {suggestion.key}{os.linesep}      ({suggestion.reason})"
        for suggestion in suggestions
    ]
    return os.linesep.join(lines)


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
    "UnsupportedFieldTypeException",
]


class AlreadyRegisteredException(Exception):
    def __init__(self, registration_key: "RegistrationKey"):
        super(AlreadyRegisteredException, self).__init__(
            f"A configuration has already been registered with the same key!"
            f"Got: {registration_key}"
        )


class NamespaceNotFoundException(Exception):
    def __init__(
        self,
        registration_key: "RegistrationKey",
        namespaces: List[str],
        missing_namespace: Optional[str] = None,
    ):
        hint = ""
        if missing_namespace is not None:
            from cinnamon.utility.suggestions import closest_string

            match = closest_string(missing_namespace, namespaces)
            hint = (
                f"{os.linesep}Did you mean namespace '{match}'?"
                if match is not None
                else ""
            )

        super(NamespaceNotFoundException, self).__init__(
            f"The registration key namespace cannot be found. {os.linesep}"
            f"Key: {registration_key}{os.linesep}"
            f"Missing namespace: {missing_namespace}{os.linesep}"
            f"Known namespaces: {namespaces}{hint}{os.linesep}"
            f"Please, make sure you add the main directory containing that namespace "
            f"when calling Registry.build()"
        )


class NotRegisteredException(Exception):
    def __init__(
        self,
        registration_key: "RegistrationKey",
        suggestions: "Optional[List[KeySuggestion]]" = None,
    ):
        super(NotRegisteredException, self).__init__(
            f"Could not find key {registration_key}. Did you register it?"
            f"{_suggestion_block(suggestions)}"
        )


class NotBoundException(Exception):
    def __init__(self, registration_key: "RegistrationKey"):
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
    def __init__(self, directory: Union[str, Path]):
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


class UnsupportedFieldTypeException(Exception):
    """A ``Configuration`` field is typed as something too heavy to configure.

    Raised in place of pydantic's schema-generation error, whose advice --
    "set ``arbitrary_types_allowed=True``" -- is correct for pydantic and
    exactly wrong here: taking it merges the component and configuration
    concepts that cinnamon exists to keep apart.
    """

    def __init__(
        self,
        configuration_name: str,
        field_type: Optional[str] = None,
        field_name: Optional[str] = None,
    ):
        where = f"Field '{field_name}' on" if field_name else "A field on"
        what = f" is annotated '{field_type}', which" if field_type else ", which"

        super().__init__(
            f"{where} configuration '{configuration_name}'{what} cannot be used "
            f"as a configuration value.{os.linesep}{os.linesep}"
            f"Configurations stay lightweight: they describe what a component "
            f"needs, they do not hold it. Either pass the parameters the object "
            f"is built from, or register it as its own component and depend on "
            f"it with a RegistrationKey:{os.linesep}"
            f"    child: RegistrationKey = RegistrationKey("
            f"name=..., namespace=...){os.linesep}{os.linesep}"
            f"Pydantic's own advice for this error -- arbitrary_types_allowed=True "
            f"-- does lift the restriction, at the cost of deep-copying that "
            f"object once per configuration and twice per variant during "
            f"expansion."
        )
