from __future__ import annotations

from typing import Optional, TypeVar, Type

import cinnamon_core.registry
import cinnamon_core.configuration

C = TypeVar('C', bound='Component')

__all__ = ['Component', 'C']


class Component:
    """
    Generic component class.
    Components generally receive data and produce other data as output: i.e., a data transformation process.
    """

    @classmethod
    def build_component(
            cls: Type[C],
            registration_key: Optional[cinnamon_core.registry.Registration] = None,
            name: Optional[str] = None,
            namespace: Optional[str] = None,
            tags: cinnamon_core.configuration.Tags = None,
    ) -> C:
        """
        Syntactic sugar for building a ``Component`` from a ``RegistrationKey`` in implicit format.

        Args:
            registration_key: the ``RegistrationKey`` used to register the ``Configuration`` class.
            name: the ``name`` field of ``RegistrationKey``
            tags: the ``tags`` field of ``RegistrationKey``
            namespace: the ``namespace`` field of ``RegistrationKey``

        Returns:
            A ``Component`` instance

        Raises:
            ``InvalidConfigurationTypeException``: if there's a mismatch between the ``Configuration`` class used
            during registration and the type of the built ``Configuration`` instance using the registered
            ``constructor`` method (see ``ConfigurationInfo`` arguments).

            ``NotBoundException``: if the ``Configuration`` is not bound to any ``Component``.
        """
        return cinnamon_core.registry.Registry.build_component(registration_key=registration_key,
                                                               name=name,
                                                               tags=tags,
                                                               namespace=namespace)
