"""
5. Depending on many registrations at once.

    python examples/tutorial/05_collections.py

A dependency field can hold a ``list`` of keys, or a ``dict`` of them keyed by
string. Use a list when order is what matters (a pipeline of stages, a set of
loss terms) and a dict when the members need names (metrics you will report
individually).

One level only: ``list[list[RegistrationKey]]`` is refused, with an error that
says so. Nesting would mean inventing a path language to address a key inside a
container, and the graph would stop being a graph over keys.
"""

from cinnamon.configuration import Configuration, Param
from cinnamon.registry import RegistrationKey, Registry

NAMESPACE = "tutorial"


def key(name: str) -> RegistrationKey:
    return RegistrationKey(name=name, namespace=NAMESPACE)


class Metric:
    def __init__(self, power: int):
        self.power = power

    def score(self, value: float) -> float:
        return round(value**self.power, 3)


class Model:
    def __init__(
        self,
        losses: list[RegistrationKey],
        metrics: dict[str, RegistrationKey],
    ):
        # Same pattern as a scalar dependency, once per member. The container
        # shape is preserved exactly, so the dict keeps its labels.
        self.losses = [Registry.from_key(k) for k in losses]
        self.metrics = {name: Registry.from_key(k) for name, k in metrics.items()}


class MetricConfig(Configuration):
    power: int = Param(1)


class ModelConfig(Configuration):
    losses: list[RegistrationKey] = Param(
        [key("cross_entropy"), key("sparsity")],
        description="Applied in order",
    )
    metrics: dict[str, RegistrationKey] = Param(
        {"accuracy": key("cross_entropy")},
        description="Reported under these names",
    )


def main() -> None:
    Registry.initialize()
    for name, power in (("cross_entropy", 1), ("sparsity", 2)):
        Registry.register_configuration(
            MetricConfig(power=power),
            name=name,
            namespace=NAMESPACE,
            component=f"{__name__}.Metric",
        )
    Registry.register_configuration(
        ModelConfig(),
        name="model",
        namespace=NAMESPACE,
        component=f"{__name__}.Model",
    )
    Registry.dag_resolution()

    model = Registry.from_key(key("model"))
    print("losses (ordered):", [loss.score(3.0) for loss in model.losses])
    print("metrics (named):  ", {n: m.score(3.0) for n, m in model.metrics.items()})

    # Every member is a real edge in the graph, so a typo in any one of them is
    # caught by `cmn-check` rather than at the moment you try to build.
    config = Registry.retrieve_configuration(registration_key=key("model"))
    print("\ndependency fields:", list(config.dependencies))

    print(
        "\nNote what a container does NOT do: a member's own variants are not"
        "\nmultiplied into the parent, the way a scalar dependency's are. Three"
        "\nlosses with three variants each would be 27 parent keys from one"
        "\nfield. To vary a container, vary the whole thing:"
        "\n    Param([A], variants=[[A, B], [A, B, C]])"
    )

    try:

        class Nested(Configuration):
            groups: list[list[RegistrationKey]] = []

        Nested().dependencies
    except TypeError as error:
        message = str(error)
        print("\nnesting is refused:")
        print("  " + message[message.index("Nested containers") :])


if __name__ == "__main__":
    main()
