from typing import Type

from cinnamon.configuration import C, Configuration
from cinnamon.registry import register_method

class MockConfig(Configuration):

    @classmethod
    @register_method(name='config', namespace='testing')
    def default(
            cls: Type[C]
    ) -> C:
        config = super().default()
        return config