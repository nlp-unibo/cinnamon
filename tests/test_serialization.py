from cinnamon.configuration import Configuration
from cinnamon.component import Component
from cinnamon.registry import RegistrationKey
from cinnamon.utility.registration import PythonSerializer
from tests.fixtures import (
    define_serializer
)
import numpy


def test_serialize_configuration_empty(
        define_serializer
):
    serializer: PythonSerializer = define_serializer
    config = Configuration()
    config.registration_key = RegistrationKey(name='config',
                                              namespace='testing')

    serializer.serialize_configuration(config=config,
                                       component_class=Component)
    print()