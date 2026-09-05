"""
Registrations for the worked project.

`Registry.build` finds every `configurations/` package under the directory it is
given, imports the modules inside, and runs whatever the `@register` and
`@register_method` decorators buffered. Nothing else about the layout matters --
`components/` is a convention, not a requirement.
"""

from cinnamon.configuration import Configuration, Param
from cinnamon.registry import RegistrationKey, Registry, register, register_method

NAMESPACE = "tutorial/summarisation"

DOCUMENT = (
    "cinnamon separates logic from configuration. Components carry the weight. "
    "Configurations describe it. That split is what makes sweeps cheap."
)


class TruncatorConfig(Configuration):
    sentences: int = Param(1, ge=1, variants=[2], description="How many to keep")

    @classmethod
    @register_method(
        name="strategy",
        tags={"truncate"},
        namespace=NAMESPACE,
        component="components.summariser.Truncator",
    )
    def default(cls):
        return super().default()


class SummariserConfig(Configuration):
    strategy: RegistrationKey = Param(
        RegistrationKey(name="strategy", tags={"truncate"}, namespace=NAMESPACE),
        description="How to shorten the document",
    )
    document: str = Param(DOCUMENT, description="Text to summarise")


# `@register` is the other entry point: a plain function that registers whatever
# it likes. Use it when a `default()` classmethod would be contrived.
@register
def register_summarisers():
    Registry.register_configuration(
        config=SummariserConfig(),
        name="summariser",
        namespace=NAMESPACE,
        component="components.summariser.Summariser",
        run_method="run",  # makes it discoverable by `cmn-run`
    )
