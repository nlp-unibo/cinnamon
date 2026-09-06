<div align="center">

# cinnamon

**A lightweight Python framework for decoupling configuration from code logic.**

[![PyPI version](https://img.shields.io/pypi/v/cinnamon-core.svg)](https://pypi.org/project/cinnamon-core/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://github.com/nlp-unibo/cinnamon/actions/workflows/ci.yml/badge.svg)](https://github.com/nlp-unibo/cinnamon/actions)

[Documentation](https://nlp-unibo.github.io/cinnamon/) · [Quickstart](https://nlp-unibo.github.io/cinnamon/quickstart.html) · [Tutorial](https://nlp-unibo.github.io/cinnamon/tutorial/index.html) · [Examples](https://nlp-unibo.github.io/cinnamon/examples/index.html)

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
- **Registry-based dependency injection** — register a `Configuration`, bind it to a component by import path, and let cinnamon build the dependency graph automatically. Your component stays a plain class: no base class, no decorator, no import of cinnamon.
- **Variants** — declare alternative parameter values alongside their defaults and enumerate every valid combination.
- **Conditions** — attach runtime invariants to configurations via `add_condition`, validated before any component is built.
- **Dependencies** — compose configurations by pointing fields at `RegistrationKey` instances, singly or as a `list`/`dict` of them; the `Registry` resolves the graph children-first, so a child's variants propagate to its parents.
- **Community-ready** — pull components and `Configuration` classes from external projects via `external_directories` and build on top of them.
- **CLI included** — `cmn-check` reports unresolved keys with suggestions and mismatched component signatures without importing your components; `cmn-build` resolves and writes the key list; `cmn-run` and `cmn-generate` run experiments and generate scripts without boilerplate.

---

## Installation

```bash
pip install cinnamon-core
```

The distribution is `cinnamon-core`; the import package is `cinnamon`:

```python
import cinnamon
```

They differ because `cinnamon` on PyPI is an unrelated project. `cinnamon-core`
is the package these releases have always used, and it supersedes the old
`cinnamon-generic`, `cinnamon-th` and `cinnamon-tf` split.

That covers the library and the two non-interactive commands, `cmn-build` and
`cmn-check`.

Optional extras:

| Extra | What it adds                                              | Install |
|---|-----------------------------------------------------------|---|
| `cli` | Interactive prompts for `cmn-run` and `cmn-generate` | `pip install "cinnamon-core[cli]"` |
| `examples` | Dependencies for the built-in examples                    | `pip install "cinnamon-core[examples]"` |
| `dev` | pytest, ruff, mypy                                        | `pip install "cinnamon-core[dev]"` |

---

## Quickstart

**1. Define a component** — a plain Python class, no base class required:

```python
class DataLoader:

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
                             variants=[16, 64])

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
loader = Registry.instantiate(name='loader', tags={'default'}, namespace='myproject')
loader.load()
```

The `Registry` builds the configuration, resolves its dependencies, validates its
conditions, and passes the resulting values to `DataLoader.__init__`.

**5. Enumerate variants** — every combination other than the all-defaults one,
which the `Registry` already registers on its own:

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
| Component | Any plain Python class, referenced by its import path (e.g. `components.DataLoader`) | [→](https://nlp-unibo.github.io/cinnamon/component.html) |
| `RegistrationKey` | A `(name, tags, namespace)` identifier that binds a config to a component | [→](https://nlp-unibo.github.io/cinnamon/registration.html) |
| `Registry` | Stores registrations, resolves the dependency DAG, and builds components | [→](https://nlp-unibo.github.io/cinnamon/registration.html) |
| Dependencies | Other registrations referenced by `RegistrationKey` fields, singly or as a `list`/`dict` | [→](https://nlp-unibo.github.io/cinnamon/dependencies.html) |

---

## Learning cinnamon

**[`examples/tutorial/`](https://github.com/nlp-unibo/cinnamon/tree/main/examples/tutorial/)** — seven runnable steps, no dependencies
beyond cinnamon itself. Each one is a single file you can read in a screen and change,
and the test suite runs every one of them on each commit.

```bash
pip install cinnamon-core
python examples/tutorial/01_configuration.py
```

The same steps, with commentary and the code included from these files, are at
[nlp-unibo.github.io/cinnamon/tutorial](https://nlp-unibo.github.io/cinnamon/tutorial/index.html).

| | Introduces |
|---|---|
| [1. Configuration](https://github.com/nlp-unibo/cinnamon/tree/main/examples/tutorial/01_configuration.py) | `Configuration`, `Param`, validation |
| [2. Registration](https://github.com/nlp-unibo/cinnamon/tree/main/examples/tutorial/02_registration.py) | components as plain classes, `RegistrationKey` |
| [3. Variants](https://github.com/nlp-unibo/cinnamon/tree/main/examples/tutorial/03_variants.py) | one component, many configurations |
| [4. Dependencies](https://github.com/nlp-unibo/cinnamon/tree/main/examples/tutorial/04_dependencies.py) | referencing another registration |
| [5. Collections](https://github.com/nlp-unibo/cinnamon/tree/main/examples/tutorial/05_collections.py) | `list` and `dict` of keys |
| [6. Conditions](https://github.com/nlp-unibo/cinnamon/tree/main/examples/tutorial/06_conditions.py) | rejecting combinations that make no sense |
| [7. Project layout](https://github.com/nlp-unibo/cinnamon/tree/main/examples/tutorial/07_project_layout/) | the real directory structure and the CLI |

Step 7 is the one to copy when starting a project of your own.

## A full example

The rest of `examples/` is a complete ML pipeline: data loading, preprocessing, SVM
classification, and evaluation on the IMDB sentiment dataset. It downloads the dataset
on first run.

```bash
pip install -e ".[examples]"
python -m examples.demos.demo_benchmark
```

See the [examples documentation](https://nlp-unibo.github.io/cinnamon/examples/index.html)
for a full walkthrough.

---

## Documentation

Full documentation is available at **[nlp-unibo.github.io/cinnamon](https://nlp-unibo.github.io/cinnamon/)**.

---

## Contributing

Contributions are welcome. [`CONTRIBUTING.md`](https://github.com/nlp-unibo/cinnamon/blob/main/CONTRIBUTING.md) covers the working
agreement: one branch per change, `nox` green before pushing, and a pull request into
`main`.

`nox` reproduces the whole CI pipeline locally in about a minute:

```bash
pip install nox
nox                  # lint, type-check, and the suite behind a 100% coverage gate
nox -s core          # the suite without the CLI extra installed
nox -s examples      # the tutorial and the scikit-learn pipeline
nox -s docs          # the documentation, warnings treated as errors
```

For questions, issues, or feature requests, open a
[GitHub issue](https://github.com/nlp-unibo/cinnamon/issues) or contact:

**Federico Ruggeri** — [federico.ruggeri6@unibo.it](mailto:federico.ruggeri6@unibo.it)

---

## License

[MIT](https://github.com/nlp-unibo/cinnamon/blob/main/LICENSE)