from typing import Type

import pytest

from cinnamon.component import Component
from cinnamon.configuration import Configuration, C
from cinnamon.registry import (
    Registry,
    RegistrationKey
)


@pytest.fixture
def reset_registry():
    Registry.initialize()


@pytest.fixture
def expand_registry():
    Registry.expanded = True


@pytest.fixture
def define_configuration():
    config = Configuration()
    config.add(name='x',
               value=10,
               type_hint=int,
               description='a parameter')
    return config


class BaseComponent(Component):

    def __init__(
            self,
            x: int,
            y: int
    ):
        self.x = x
        self.y = y


class BaseConfig(Configuration):

    @classmethod
    def default(
            cls: Type[C]
    ) -> C:
        config = super().default()

        config.add(name='x',
                   value=5,
                   type_hint=int)
        config.add(name='y',
                   value=10,
                   type_hint=int)
        return config


class InvalidConfig(Configuration):

    @classmethod
    def default(
            cls: Type[C]
    ) -> C:
        config = super().default()
        config.add(name='x', value=5, allowed_range=lambda x: x in [2, 3])
        return config


class ChildConfig(Configuration):

    @classmethod
    def default(
            cls: Type[C]
    ) -> C:
        config = super().default()
        config.add(name='y', variants=[False, True])
        return config


class ChildComponent(Component):

    def __init__(
            self,
            y: bool
    ):
        self.y = y


class ConfigWithChild(Configuration):

    @classmethod
    def default(
            cls: Type[C]
    ) -> C:
        config = super().default()
        config.add(name='c1', value=RegistrationKey(name='test', tags={'t2'}, namespace='testing'))
        return config

class ConfigWithVariantChild(Configuration):

    @classmethod
    def default(
            cls: Type[C]
    ) -> C:
        config = super().default()
        config.add(name='c1', value=RegistrationKey(name='test', tags={'x=1'}, namespace='testing'))
        return config


class ComponentWithChild(Component):

    def __init__(
            self,
            c1
    ):
        self.c1 = c1


class VariantConfig(Configuration):

    @classmethod
    def default(
            cls: Type[C]
    ) -> C:
        config = super().default()
        config.add(name='x', variants=[1, 2, 3])
        return config


class InvalidVariantConfig(Configuration):

    @classmethod
    def default(
            cls: Type[C]
    ) -> C:
        config = super().default()
        config.add(name='x', value=5, variants=[1, 2, 3], allowed_range=lambda x: x in [1, 2, 5])
        return config


class VariantConfigWithChild(Configuration):

    @classmethod
    def default(
            cls: Type[C]
    ) -> C:
        config = super().default()
        config.add(name='x', variants=[1, 2, 3])
        config.add(name='c1', value=RegistrationKey(name='test', tags={'t2'}, namespace='testing'))
        return config


class VariantConfigWithVariantChild(Configuration):

    @classmethod
    def default(
            cls: Type[C]
    ) -> C:
        config = super().default()
        config.add(name='y', variants=['a', 'b'], is_required=True)
        config.add(name='c1', type_hint=RegistrationKey, variants=[
            RegistrationKey(name='test', tags={'t3'}, namespace='testing')
        ],
                   is_required=True)
        return config


class CliqueConfigA(Configuration):

    @classmethod
    def default(
            cls: Type[C]
    ) -> C:
        config = super().default()
        config.add(name='child', value=RegistrationKey(name='config', tags={'c2'}, namespace='testing'))
        return config


class CliqueConfigB(Configuration):

    @classmethod
    def default(
            cls: Type[C]
    ) -> C:
        config = super().default()
        config.add(name='child', value=RegistrationKey(name='config', tags={'c1'}, namespace='testing'))
        return config


class ConfigWithExternalDependency(Configuration):

    @classmethod
    def default(
            cls: Type[C]
    ) -> C:
        config = super().default()
        config.add(name='c1', value=RegistrationKey(name='test', namespace='external'))
        return config
