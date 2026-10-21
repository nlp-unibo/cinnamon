"""Every key the library registers, declared once."""

from cinnamon import Namespace

NAMESPACE = Namespace("library")

ENCODER = NAMESPACE.key("encoder")
HEAD = NAMESPACE.key("head")
MODEL = NAMESPACE.key("model")
TASK = NAMESPACE.key("task", description="the library's own smoke task")
