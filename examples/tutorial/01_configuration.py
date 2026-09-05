"""
1. A configuration is a typed, documented parameter set.

    python examples/tutorial/01_configuration.py

Nothing is registered yet -- this step is only about what a ``Configuration``
is, because everything later is built on it.

The rule to carry forward: **components carry the weight, configurations
describe it.** A configuration holds the parameters a component needs. It never
holds the component, or a model, or a database handle. Keeping it light is what
makes it cheap to write fifty of them, which is the whole point of the library.
"""

from cinnamon.configuration import Configuration, Param


class TokenizerConfig(Configuration):
    """Parameters for a tokenizer. Plain types, with defaults."""

    lowercase: bool = Param(True, description="Fold text to lower case first")
    max_tokens: int = Param(
        512,
        ge=1,  # any pydantic constraint works
        description="Truncate sequences beyond this many tokens",
    )
    separator: str = Param(" ", description="Token separator")


def main() -> None:
    config = TokenizerConfig()
    print("defaults:          ", config.values)

    # Override at construction, exactly like any pydantic model.
    custom = TokenizerConfig(max_tokens=128, lowercase=False)
    print("overridden:        ", custom.values)

    # Constraints are enforced when the value is set, not when it is used.
    try:
        TokenizerConfig(max_tokens=0)
    except Exception as error:
        print("max_tokens=0 ->    ", type(error).__name__, "(ge=1 rejected it)")

    # Descriptions stay attached to the fields, so a configuration documents
    # itself. `cmn-build` and the CLI prompts read them back.
    print("\nfields:")
    for name, field in TokenizerConfig.model_fields.items():
        print(f"  {name:12s} {str(field.annotation.__name__):6s} {field.description}")

    # Try this: uncomment the following and run again. cinnamon refuses it and
    # explains why -- a configuration that holds a live object has stopped
    # describing a component and started being one.
    #
    #     import sqlite3
    #     class Leaky(Configuration):
    #         connection: sqlite3.Connection = None


if __name__ == "__main__":
    main()
