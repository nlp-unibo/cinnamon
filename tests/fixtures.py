from typing import Literal, Type

import pytest

from cinnamon.configuration import C, Configuration, Param
from cinnamon.registry import RegistrationKey, Registry


@pytest.fixture
def reset_registry():
    Registry.initialize()


@pytest.fixture
def expand_registry():
    Registry.expanded = True


class EmptyComponent:
    pass


class BaseComponent:
    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y


class BaseConfig(Configuration):
    x: int = 5
    y: int = 10

    @classmethod
    def default(cls: Type[C]) -> C:
        return cls(x=5, y=10)


class ConfigWithVariants(Configuration):
    x: int = Param(1, variants=[2, 3])


class ConfigWithNonTaggableVariants(Configuration):
    x: list[int] = Param([1, 2, 3], variants=[[2, 2]])


class ConfigWithMultipleVariants(Configuration):
    x: int = Param(1, variants=[2, 3])
    y: int = Param(2, variants=[3, 4])


class InvalidConfig(Configuration):
    x: int = Param(5, le=3, ge=2)


class ChildConfig(Configuration):
    y: bool = Param(False, variants=[True])


class ChildComponent:
    def __init__(self, y: bool):
        self.y = y


class NestedConfig(Configuration):
    x: int = 10
    child: BaseConfig = BaseConfig.default()


class ConfigWithChild(Configuration):
    c1: RegistrationKey = RegistrationKey(name="test", tags={"t2"}, namespace="testing")


class ConfigWithVariantChild(Configuration):
    c1: RegistrationKey = RegistrationKey(name="test", namespace="testing")


class ComponentWithChild:
    def __init__(self, c1):
        self.c1 = c1


class InvalidVariantConfig(Configuration):
    x: Literal[1, 2, 5] = Param(5, variants=[1, 2, 3])


class VariantConfigWithChild(Configuration):
    x: int = Param(1, variants=[2, 3])
    c1: RegistrationKey = RegistrationKey(name="test", tags={"t2"}, namespace="testing")


class VariantConfigWithVariantChild(Configuration):
    y: str = Param("a", variants=["b"])
    c1: RegistrationKey = RegistrationKey(name="test", tags={"t3"}, namespace="testing")


class CliqueConfigA(Configuration):
    child: RegistrationKey = RegistrationKey(
        name="config", tags={"c2"}, namespace="testing"
    )


class CliqueConfigB(Configuration):
    child: RegistrationKey = RegistrationKey(
        name="config", tags={"c1"}, namespace="testing"
    )


class ConfigWithExternalDependency(Configuration):
    c1: RegistrationKey = RegistrationKey(name="test", namespace="external")


class ParentWithVariantsAndChild(Configuration):
    x: int = Param(1, variants=[2])
    child: RegistrationKey = RegistrationKey(name="intermediate", namespace="testing")


class IntermediateWithChild(Configuration):
    canarin: int = 4
    child: RegistrationKey = RegistrationKey(name="leaf", namespace="testing")

    @classmethod
    def custom_method(cls) -> C:
        return cls(canarin=10)


class LeafWithVariants(Configuration):
    x: int = Param(1, variants=[2])


class CustomRunnableComponent:
    def run(self):
        return "this is a mock runnable component"


class CustomRunnableComponentWithArgs:
    def __init__(self, x: int):
        self.x = x

    def run(self):
        return self.x
