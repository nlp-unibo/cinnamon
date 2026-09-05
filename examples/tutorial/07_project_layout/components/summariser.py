"""Components for the worked project: plain classes, no cinnamon imports needed."""

from cinnamon.registry import RegistrationKey, Registry


class Truncator:
    """Keeps the first `sentences` sentences."""

    def __init__(self, sentences: int):
        self.sentences = sentences

    def summarise(self, text: str) -> str:
        parts = [part.strip() for part in text.split(".") if part.strip()]
        return ". ".join(parts[: self.sentences]) + "."


class Summariser:
    """A runnable component: `cmn-run` calls its `run` method."""

    def __init__(self, strategy: RegistrationKey, document: str):
        self.strategy = Registry.from_key(strategy)
        self.document = document

    def run(self) -> str:
        summary = self.strategy.summarise(self.document)
        print(f"summary: {summary}")
        return summary
