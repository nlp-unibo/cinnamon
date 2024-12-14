from typing import Type

from cinnamon.component import Component, RunnableComponent
from cinnamon.configuration import Configuration, C
from cinnamon.registry import register_method


class MockConfiguration(Configuration):

    @classmethod
    @register_method(name='config', tags={'nest2'}, namespace='testing', component_class=RunnableComponent)
    @register_method(name='config', tags={'nest1'}, namespace='testing', component_class=Component)
    def default(
            cls: Type[C]
    ) -> C:
        config = super().default()
        return config
