"""The study subclasses the library's configurations and overrides values only.

Its model keeps the library's encoder key, so building the study loads the
library's registrations through that dependency.
"""

from typing import Sequence

from cinnamon import Param, RegistrationKey, register_class
from downstream.library.configurations.models import ModelConfig, TaskConfig
from downstream.study.configurations.keys import MODEL, TASK


@register_class(key=MODEL, component="downstream.library.components.Model")
class StudyModelConfig(ModelConfig):
    depth: int = Param(2, ge=1)


@register_class(
    key=TASK, component="downstream.library.components.Task", run_method="run"
)
class StudyTaskConfig(TaskConfig):
    model: RegistrationKey = Param(MODEL)
    seeds: Sequence[int] = Param([1, 2, 3])
