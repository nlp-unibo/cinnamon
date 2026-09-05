"""
3. Variants -- one component, many configurations.

    python examples/tutorial/03_variants.py

This is what cinnamon is for. A researcher rarely wants *a* configuration; they
want the twelve configurations that differ along two axes, each addressable and
reproducible. Declare the axes, and resolution enumerates the combinations for
you, giving each one a stable key.
"""

from cinnamon.configuration import Configuration, Param
from cinnamon.registry import Registry


class Classifier:
    def __init__(self, learning_rate: float, hidden_size: int, dropout: float):
        self.learning_rate = learning_rate
        self.hidden_size = hidden_size
        self.dropout = dropout

    def describe(self) -> str:
        return (
            f"lr={self.learning_rate} hidden={self.hidden_size} dropout={self.dropout}"
        )


class ClassifierConfig(Configuration):
    # `variants` lists the *alternatives* to the default. The default itself is
    # index 0 and always stays in the sweep.
    learning_rate: float = Param(1e-3, variants=[1e-2, 1e-4])
    hidden_size: int = Param(128, variants=[256])
    dropout: float = Param(0.1, description="Not varied: stays fixed everywhere")


def main() -> None:
    Registry.initialize()
    Registry.register_configuration(
        config=ClassifierConfig(),
        name="classifier",
        namespace="tutorial",
        component=f"{__name__}.Classifier",
    )

    valid_keys, _ = Registry.dag_resolution()

    # 3 learning rates x 2 hidden sizes = 6 configurations, from six lines.
    print(f"{len(valid_keys)} configurations generated:\n")
    for key in sorted(valid_keys, key=str):
        component = Registry.from_key(key)
        tags = ", ".join(sorted(key.tags)) or "(defaults)"
        print(f"  {tags:36s} -> {component.describe()}")

    print(
        "\nThe tags are derived from the values, so a key is stable across runs:"
        "\nrerun this file and 'learning_rate=0.01--hidden_size=256' still names"
        "\nthe same experiment. That is what makes results addressable."
    )


if __name__ == "__main__":
    main()
