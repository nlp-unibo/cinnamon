from __future__ import annotations

from typing import Optional, TypeVar, Type

import cinnamon.configuration
import cinnamon.registry

C = TypeVar('C', bound='Component')

__all__ = [
    'Component',
    'RunnableComponent'
]


class Component:
    """
    A component defines any logic of a program, including data loading, data visualization, and model training.
    """

    @classmethod
    def build_component(
            cls: Type[C],
            registration_key: Optional[cinnamon.registry.Registration] = None,
            name: Optional[str] = None,
            namespace: Optional[str] = None,
            tags: cinnamon.configuration.Tags = None,
            **build_args
    ) -> C:
        """
        Syntactic sugar for building a ``Component`` from a ``RegistrationKey`` in implicit format.

        Args:
            registration_key: the ``RegistrationKey`` used to register the ``Configuration`` class.
            name: the ``name`` field of ``RegistrationKey``
            tags: the ``tags`` field of ``RegistrationKey``
            namespace: the ``namespace`` field of ``RegistrationKey``
            build_args: additional custom component constructor args

        Returns:
            A ``Component`` instance

        Raises:
            ``InvalidConfigurationTypeException``: if there's a mismatch between the ``Configuration`` class used
            during registration and the type of the built ``Configuration`` instance using the registered
            ``constructor`` method (see ``ConfigurationInfo`` arguments).

            ``NotBoundException``: if the ``Configuration`` is not bound to any ``Component``.
        """
        return cinnamon.registry.Registry.build_component(registration_key=registration_key,
                                                          name=name,
                                                          tags=tags,
                                                          namespace=namespace,
                                                          **build_args)


class RunnableComponent(Component):
    """
    A Component that can be executed as standalone through command-line.
    """

    def run(
            self
    ):
        """
        Run interface to execute components.
        """
        raise NotImplementedError(f"A {RunnableComponent} instance must implement the `run` method.")
