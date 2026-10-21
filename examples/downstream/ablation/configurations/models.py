"""Library configurations, subclassed with values and keys of the ablation's own.

Importing the library's configuration module runs its registrations too, so
a build of this project registers the library's keys without depending on
any of them.
"""

from cinnamon import Param, RegistrationKey, register_class
from downstream.ablation.configurations.keys import ENCODER, HEAD, MODEL
from downstream.library.configurations.models import (
    EncoderConfig,
    HeadConfig,
    ModelConfig,
)


@register_class(key=ENCODER, component="downstream.library.components.Encoder")
class AblationEncoderConfig(EncoderConfig):
    size: int = Param(1, ge=1)


@register_class(key=HEAD, component="downstream.library.heads.Head")
class AblationHeadConfig(HeadConfig):
    classes: int = Param(2, ge=2)


@register_class(key=MODEL, component="downstream.library.components.Model")
class AblationModelConfig(ModelConfig):
    encoder: RegistrationKey = Param(ENCODER)
    head: RegistrationKey = Param(HEAD)
