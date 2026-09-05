"""
2. Binding a configuration to a component, and building it.

    python examples/tutorial/02_registration.py

A component is an ordinary class -- no base class, no decorator. cinnamon needs
only its *import path*, as a string, which it resolves when you ask for an
instance and not before. That is what keeps a build independent of how heavy
your components are: nothing imports torch to look at a registry.
"""

from cinnamon.configuration import Configuration, Param
from cinnamon.registry import RegistrationKey, Registry


class Tokenizer:
    """A component: it does the work, and it is a plain class."""

    def __init__(self, lowercase: bool, separator: str):
        self.lowercase = lowercase
        self.separator = separator

    def tokenize(self, text: str) -> list[str]:
        return (text.lower() if self.lowercase else text).split(self.separator)


class TokenizerConfig(Configuration):
    lowercase: bool = Param(True, description="Fold text to lower case first")
    separator: str = Param(" ", description="Token separator")


def main() -> None:
    Registry.initialize()

    # A registration is (configuration, name, namespace, tags) -> component.
    # In a real project you would put this in a `configurations/` package and
    # let `Registry.build` discover it; step 7 shows that. Registering by hand
    # keeps this file readable in one screen.
    Registry.register_configuration(
        config=TokenizerConfig(),
        name="tokenizer",
        namespace="tutorial",
        # Normally "mypackage.components.Tokenizer". Inside a script the module
        # is __main__, so that is the path cinnamon needs.
        component=f"{__name__}.Tokenizer",
    )

    # Resolution walks the dependency graph and validates every configuration.
    valid_keys, invalid_keys = Registry.dag_resolution()
    print(f"valid: {len(valid_keys)}   invalid: {len(invalid_keys)}")

    # A RegistrationKey is how you name a registration: name + namespace + tags.
    key = RegistrationKey(name="tokenizer", namespace="tutorial")
    print("key:  ", key)

    # ... and how you ask for the component. The class is imported now, at the
    # moment it is needed.
    tokenizer = Registry.from_key(key)
    print("built:", type(tokenizer).__name__)
    print("work: ", tokenizer.tokenize("The Quick Brown Fox"))

    # The configuration itself is retrievable too, without building anything.
    config = Registry.retrieve_configuration(registration_key=key)
    print("config:", config.values)


if __name__ == "__main__":
    main()
