__version__ = "2.2.1"

# Re-exported so ``from cinnamon import Configuration, Registry`` works. Each
# module's ``__all__`` decides what is public, so this list cannot drift.
from cinnamon import configuration, registry  # noqa: E402
from cinnamon.configuration import *  # noqa: E402, F403
from cinnamon.registry import *  # noqa: E402, F403

__all__ = [*configuration.__all__, *registry.__all__]
