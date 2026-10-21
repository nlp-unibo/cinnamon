"""Every key this repo registers, declared once."""

from cinnamon.registry import Namespace

NAMESPACE = Namespace("keyed")

BASE = NAMESPACE.key("base", description="the smallest configuration")
DERIVED = NAMESPACE.key("derived", "big")
METHOD = NAMESPACE.key("method")
CALLED = NAMESPACE.key("called")
