<div align="center">

# cinnamon

**A lightweight Python framework for decoupling configuration from code logic.**

[![PyPI version](https://img.shields.io/pypi/v/cinnamon.svg)](https://pypi.org/project/cinnamon/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://github.com/nlp-unibo/cinnamon/actions/workflows/ci.yml/badge.svg)](https://github.com/nlp-unibo/cinnamon/actions)

[Documentation](https://nlp-unibo.github.io/cinnamon/) · [Examples](https://nlp-unibo.github.io/cinnamon/examples/index.html) · [Quickstart](https://nlp-unibo.github.io/cinnamon/quickstart.html)

</div>

---

## What is cinnamon?

Cinnamon separates **what your code does** from **how it is configured**.

Instead of scattering parameters across constructors, config files, or command-line
arguments, you define each component's parameters as a typed `Configuration` class
backed by [Pydantic](https://docs.pydantic.dev/). You then register that configuration
in the `Registry` and bind it to your component. From that point on, the `Registry`
handles construction, validation, type-checking, and dependency resolution automatically.

The result is a project where every component is independently swappable, every
parameter is validated and documented, and the full experiment can be reproduced by a
single `RegistrationKey`.

---

## Features

- **Pydantic-backed configurations** — field types, constraints (`ge`, `le`, `Literal`), and cross-field validators via `@model_validator`.
- **Registry-based dependency injection** — register a `Configuration`, bind it to a `Component`, and let cinnamon build the dependency graph automatically.
- **Variants** — declare alternative parameter values alongside their defaults and enumerate every valid combination.
- **Conditions** — attach runtime invariants to configurations via `add_condition`, validated before any component is built.
- **Dependency nesting** — compose configurations by pointing fields at `RegistrationKey` instances; the `Registry` resolves the dependency graph bottom-up.
- **Community-ready** — import `Component` and `Configuration` from external projects via `external_directories` and build on top of them.
- **CLI included** — `cmn-build`, `cmn-run`, and `cmn-generate` for running and generating experiment scripts without boilerplate.

---

## Installation

```bash
pip install cinnamon
```

Optional extras:

| Extra | What it adds                                              | Install |
|---|-----------------------------------------------------------|---|
| `cli` | `cmn-build`, `cmn-run`, `cmn-generate` interactive prompts | `pip install "cinnamon[cli]"` |
| `examples` | Dependencies for the built-in examples                    | `pip install "cinnamon[examples]"` |
| `dev` | pytest, ruff, mypy                                        | `pip install "cinnamon[dev]"` |

---

## Quickstart

**1. Define a component** — plain Python, inherits from `Component`:

```python
from cinnamon.component import Component

class DataLoader(Component):

    def __init__(self, folder_name: str, batch_size: int):
        self.folder_name = folder_name
        self.batch_size  = batch_size

    def load(self):
        ...
```

**2. Define its configuration** — a Pydantic model with typed, documented fields:

```python
from cinnamon.configuration import Configuration, Param
from cinnamon.registry import register_method

class DataLoaderConfig(Configuration):
    folder_name: str = Param('data/', description='Root data directory')
    batch_size: int  = Param(32, ge=1,  description='Samples per batch',
                             variants=[16, 32, 64])

    @classmethod
    @register_method(name='loader', tags={'default'}, namespace='myproject',
                     component='components.DataLoader')
    def default(cls) -> 'DataLoaderConfig':
        return super().default()
```

**3. Build the registry** — cinnamon scans your `configurations/` folder and resolves dependencies:

```python
from pathlib import Path
from cinnamon.registry import Registry

Registry.build(directory=Path('.'))
```

**4. Instantiate** — retrieve and build a component from its registration key:

```python
loader = DataLoader.instantiate(name='loader', tags={'default'}, namespace='myproject')
loader.load()
```

**5. Enumerate variants** — generate every parameter combination automatically:

```python
config = DataLoaderConfig.default()
for combo in config.variants:
    variant = config.model_copy(update=combo['values'])
    loader = DataLoader(**variant.values)
```

That's it. See the [full quickstart](https://nlp-unibo.github.io/cinnamon/quickstart.html)
for the complete walkthrough.

---

## Key concepts

| Concept | Description | Docs |
|---|---|---|
| `Configuration` | A Pydantic `BaseModel` holding typed, validated parameters | [→](https://nlp-unibo.github.io/cinnamon/configuration.html) |
| `Param` | A `Field` wrapper that adds `tags`, `variants`, and cinnamon metadata | [→](https://nlp-unibo.github.io/cinnamon/configuration.html) |
| `Component` | Any class that inherits from `Component` | [→](https://nlp-unibo.github.io/cinnamon/component.html) |
| `RegistrationKey` | A `(name, tags, namespace)` identifier that binds a config to a component | [→](https://nlp-unibo.github.io/cinnamon/registration.html) |
| `Registry` | Stores registrations, resolves the dependency DAG, and builds components | [→](https://nlp-unibo.github.io/cinnamon/registration.html) |
| Dependencies | Nested configurations declared as `RegistrationKey` fields | [→](https://nlp-unibo.github.io/cinnamon/dependencies.html) |

---

## Examples

The `examples/` folder contains a complete ML pipeline: data loading, preprocessing,
SVM classification, and evaluation on the IMDB sentiment dataset.

```bash
pip install "cinnamon[examples]"
cd examples && python demos/demo_benchmark.py
```

See the [examples documentation](https://nlp-unibo.github.io/cinnamon/examples/index.html)
for a full walkthrough.

---

## Documentation

Full documentation is available at **[nlp-unibo.github.io/cinnamon](https://nlp-unibo.github.io/cinnamon/)**.

---

## Contributing

Contributions are welcome. To add new components and configurations, open a pull request
with your implementation and a matching entry in the examples or tests.

For questions, issues, or feature requests, open a
[GitHub issue](https://github.com/nlp-unibo/cinnamon/issues) or contact:

**Federico Ruggeri** — [federico.ruggeri6@unibo.it](mailto:federico.ruggeri6@unibo.it)

---

## License

[MIT](LICENSE)