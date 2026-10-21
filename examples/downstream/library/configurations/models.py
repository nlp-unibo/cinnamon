"""The library's configurations. A study subclasses them and changes values."""

from typing import Sequence

from cinnamon import Configuration, Param, RegistrationKey, register_class
from downstream.library.configurations.keys import ENCODER, HEAD, MODEL, TASK
from downstream.library.heads import Head


@register_class(key=ENCODER, component="downstream.library.components.Encoder")
class EncoderConfig(Configuration):
    size: int = Param(4, ge=1)


@register_class(key=HEAD, component="downstream.library.heads.Head")
class HeadConfig(Configuration):
    classes: int = Param(3, ge=2)


@register_class(key=MODEL, component="downstream.library.components.Model")
class ModelConfig(Configuration):
    encoder: RegistrationKey = Param(ENCODER)
    head: RegistrationKey[Head] = Param(HEAD)
    depth: int = Param(1, ge=1)


@register_class(
    key=TASK, component="downstream.library.components.Task", run_method="run"
)
class TaskConfig(Configuration):
    model: RegistrationKey = Param(MODEL)
    seeds: Sequence[int] = Param([42])
