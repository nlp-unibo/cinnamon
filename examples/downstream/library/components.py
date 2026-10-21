"""The library's components. Each one builds its children from their keys."""

from typing import Dict, List, Sequence

from cinnamon import RegistrationKey, Registry


class Encoder:
    def __init__(self, size: int):
        self.size = size


class Model:
    def __init__(self, encoder: RegistrationKey, head: RegistrationKey, depth: int):
        self.encoder = Registry.from_key(encoder, expected_type=Encoder)
        self.head = Registry.from_key(head)
        self.depth = depth


class Task:
    """Builds its model once per seed, in this process or in a worker."""

    def __init__(self, model: RegistrationKey, seeds: Sequence[int]):
        self.model = model
        self.seeds = list(seeds)

    def run(self) -> Dict[str, List[int]]:
        sizes = [
            Registry.from_key(self.model, expected_type=Model).encoder.size
            for _ in self.seeds
        ]
        return {"seeds": self.seeds, "sizes": sizes}


def build_in_worker(runtime: dict, key: RegistrationKey) -> int:
    """Run in a spawned process that scanned nothing, as a search worker does."""
    Registry.install_runtime(runtime)
    return Registry.from_key(key, expected_type=Model).encoder.size
