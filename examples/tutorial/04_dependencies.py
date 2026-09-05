"""
4. Dependencies -- configurations that reference other registrations.

    python examples/tutorial/04_dependencies.py

A field typed as ``RegistrationKey`` is a dependency. cinnamon records it as an
edge in the dependency graph, so it knows what a pipeline is made of before
anything is built.

Note what the *component* receives: the key itself, not a built object. The
component decides when -- and whether -- to build its child. That laziness is
deliberate; it is also why a dependency can be swapped without touching the
parent's code.
"""

from cinnamon.configuration import Configuration, Param
from cinnamon.registry import RegistrationKey, Registry

NAMESPACE = "tutorial"


class Tokenizer:
    def __init__(self, lowercase: bool):
        self.lowercase = lowercase

    def tokenize(self, text: str) -> list[str]:
        return (text.lower() if self.lowercase else text).split()


class Pipeline:
    def __init__(self, tokenizer: RegistrationKey, max_tokens: int):
        # The child is built here, by the component, from the key it was given.
        self.tokenizer = Registry.from_key(tokenizer)
        self.max_tokens = max_tokens

    def run(self, text: str) -> list[str]:
        return self.tokenizer.tokenize(text)[: self.max_tokens]


class TokenizerConfig(Configuration):
    # A variant here will show up on the *pipeline* too, further down.
    lowercase: bool = Param(True, variants=[False])


class PipelineConfig(Configuration):
    tokenizer: RegistrationKey = Param(
        RegistrationKey(name="tokenizer", namespace=NAMESPACE),
        description="Which tokenizer this pipeline uses",
    )
    max_tokens: int = Param(4)


def main() -> None:
    Registry.initialize()

    Registry.register_configuration(
        TokenizerConfig(),
        name="tokenizer",
        namespace=NAMESPACE,
        component=f"{__name__}.Tokenizer",
    )
    Registry.register_configuration(
        PipelineConfig(),
        name="pipeline",
        namespace=NAMESPACE,
        component=f"{__name__}.Pipeline",
    )

    valid_keys, _ = Registry.dag_resolution()

    pipeline_key = RegistrationKey(name="pipeline", namespace=NAMESPACE)

    # `dependencies` reports the fields cinnamon treats as graph edges.
    config = Registry.retrieve_configuration(registration_key=pipeline_key)
    print("pipeline depends on:")
    for field_name, dependency in config.dependencies.items():
        print(f"  {field_name} -> {dependency}")

    pipeline = Registry.from_key(pipeline_key)
    print("\nresult:", pipeline.run("The Quick Brown Fox Jumps Over"))

    # The tokenizer's own variant propagates: the pipeline gains a key per
    # child variant, tagged with which child it was built against. Sweeps
    # compose down the graph without anyone wiring them together.
    print("\nevery pipeline configuration resolution produced:")
    for key in sorted((k for k in valid_keys if k.name == "pipeline"), key=str):
        built = Registry.from_key(key)
        tags = ", ".join(sorted(key.tags)) or "(defaults)"
        print(f"  {tags:28s} lowercase={built.tokenizer.lowercase}")


if __name__ == "__main__":
    main()
