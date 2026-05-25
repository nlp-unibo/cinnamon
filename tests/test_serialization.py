import os

from cinnamon.component import Component
from cinnamon.configuration import Configuration
from cinnamon.registry import RegistrationKey
from cinnamon.utility.registration import PythonSerializer
from tests.fixtures import (
    define_serializer,
    BaseComponent
)

import numpy as np


def test_serialize_configuration_empty(
        define_serializer
):
    serializer: PythonSerializer = define_serializer
    config = Configuration()
    config.registration_key = RegistrationKey(name='config',
                                              namespace='testing')

    serializer.serialize_configuration(config=config,
                                       component_class=Component)

    serializer_string = serializer.build_serialization_string()

    imports = [
        'from cinnamon.registry import register, Registry',
        'from cinnamon.configuration import Configuration',
        'from cinnamon.component import Component',
    ]

    configs = [
        '@register',
        'def register_configuration_1():',
        '\tconfig = Configuration()',
        f"{os.linesep}\tRegistry.register_configuration(config=config, name='config', tags=set(), namespace='testing', component_class=Component)",
    ]

    expected_string = f"""
# Generated automatically

{os.linesep.join(imports)}

{os.linesep.join(configs)}
"""
    assert serializer_string == expected_string


def test_serialize_configuration_builtins_param(
        define_serializer
):
    serializer: PythonSerializer = define_serializer
    config = Configuration()
    config.add(name='x', value=5)
    config.registration_key = RegistrationKey(name='config',
                                              namespace='testing')

    serializer.serialize_configuration(config=config,
                                       component_class=Component)

    serializer_string = serializer.build_serialization_string()

    imports = [
        'from cinnamon.registry import register, Registry',
        'from cinnamon.configuration import Configuration',
        'from cinnamon.component import Component',
    ]

    configs = [
        '@register',
        'def register_configuration_1():',
        '\tconfig = Configuration()',
        "\tconfig.add(name='x', value=5, description=None)",
        f"{os.linesep}\tRegistry.register_configuration(config=config, name='config', tags=set(), namespace='testing', component_class=Component)",
    ]

    expected_string = f"""
# Generated automatically

{os.linesep.join(imports)}

{os.linesep.join(configs)}
"""
    assert serializer_string == expected_string


def test_serialize_configuration_custom_param(
        define_serializer
):
    serializer: PythonSerializer = define_serializer
    config = Configuration()
    config.add(name='x', value=np.array([1, 2, 3]))
    config.registration_key = RegistrationKey(name='config',
                                              namespace='testing')

    serializer.serialize_configuration(config=config,
                                       component_class=Component)

    serializer_string = serializer.build_serialization_string()

    imports = [
        'from cinnamon.registry import register, Registry',
        'from cinnamon.configuration import Configuration',
        'from numpy import array',
        'from cinnamon.component import Component',
    ]

    configs = [
        '@register',
        'def register_configuration_1():',
        '\tconfig = Configuration()',
        "\tconfig.add(name='x', value=array([1, 2, 3]), description=None)",
        f"{os.linesep}\tRegistry.register_configuration(config=config, name='config', tags=set(), namespace='testing', component_class=Component)",
    ]

    expected_string = f"""
# Generated automatically

{os.linesep.join(imports)}

{os.linesep.join(configs)}
"""
    assert serializer_string == expected_string


def test_serialize_configuration_custom_class_param(
        define_serializer
):
    serializer: PythonSerializer = define_serializer
    config = Configuration()
    config.add(name='x', value=BaseComponent(x=5, y=3))
    config.registration_key = RegistrationKey(name='config',
                                              namespace='testing')

    serializer.serialize_configuration(config=config,
                                       component_class=Component)

    serializer_string = serializer.build_serialization_string()

    imports = [
        'from cinnamon.registry import register, Registry',
        'from cinnamon.configuration import Configuration',
        'from tests.fixtures import BaseComponent',
        'from cinnamon.component import Component',
    ]

    configs = [
        '@register',
        'def register_configuration_1():',
        '\tconfig = Configuration()',
        "\tconfig.add(name='x', value=BaseComponent(x=5, y=3), description=None)",
        f"{os.linesep}\tRegistry.register_configuration(config=config, name='config', tags=set(), namespace='testing', component_class=Component)",
    ]

    expected_string = f"""
# Generated automatically

{os.linesep.join(imports)}

{os.linesep.join(configs)}
"""
    assert serializer_string == expected_string