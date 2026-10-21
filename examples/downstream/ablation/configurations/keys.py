"""The ablation's keys. None of its configurations names a library key."""

from cinnamon import Namespace

NAMESPACE = Namespace("ablation")

ENCODER = NAMESPACE.key("encoder")
HEAD = NAMESPACE.key("head")
MODEL = NAMESPACE.key("model")
