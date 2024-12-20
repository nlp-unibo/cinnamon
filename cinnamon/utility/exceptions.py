import os
from pathlib import Path
from typing import List, Union, AnyStr

class AlreadyExistingParameterException(Exception):

    def __init__(
            self,
            param: "cinnamon.configuration.Param"
    ):
        super().__init__(f'Parameter {param.name} already exists! {os.linesep}'
                         f'Parameter: {param}')


class AlreadyRegisteredException(Exception):

    def __init__(
            self,
            registration_key: "cinnamon.registry.RegistrationKey"
    ):
        super(AlreadyRegisteredException, self).__init__(
            f'A configuration has already been registered with the same key!'
            f'Got: {registration_key}')


class NamespaceNotFoundException(Exception):

    def __init__(
            self,
            registration_key: "cinnamon.registry.RegistrationKey",
            namespaces: List[str]
    ):
        super(NamespaceNotFoundException, self).__init__(
            f'The given registration key contains a namespace that cannot be found. {os.linesep}'
            f'Key: {registration_key}{os.linesep}'
            f'Namespaces: {namespaces}')


class NotRegisteredException(Exception):

    def __init__(
            self,
            registration_key: "cinnamon.registry.RegistrationKey"
    ):
        super(NotRegisteredException, self).__init__(f"Could not find registered configuration {registration_key}."
                                                     f" Did you register it?")


class NotBoundException(Exception):

    def __init__(
            self,
            registration_key: "cinnamon.registry.RegistrationKey"
    ):
        super(NotBoundException, self).__init__(
            f'Registered configuration {registration_key} is not bound to any component.'
            f' Did you bind it?')


class DisconnectedGraphException(Exception):

    def __init__(
            self,
            nodes
    ):
        super().__init__(f'Disconnected graph! Nodes {nodes} are not connected!')


class NotADAGException(Exception):

    def __init__(
            self,
            edges
    ):
        super().__init__(f'The built graph is not a DAG! {os.linesep}'
                         f'Please find below the edge list: {os.linesep}'
                         f'{self.build_edge_view(edges)}')

    def build_edge_view(
            self,
            edges
    ):
        view = []
        for edge in edges:
            node_view = f'{edge[0]} -> {edge[1]}'
            view.append(node_view)
        return os.linesep.join(view)


class AlreadyExpandedException(Exception):

    def __init__(
            self
    ):
        super().__init__(f'The registration graph has already been expanded! No further registrations are allowed.')


class NotExpandedException(Exception):

    def __init__(
            self
    ):
        super().__init__(f'The registration graph has yet to be expanded! Configuration retrieval is not allowed.')


class InvalidDirectoryException(Exception):

    def __init__(
            self,
            directory: Union[AnyStr, Path]
    ):
        super().__init__(f'The provided directory path does not exist or is not a directory. {os.linesep}'
                         f'Path: {directory}')
