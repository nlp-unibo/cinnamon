# cinnamon tutorial

Seven steps, each a runnable file. No dependencies beyond cinnamon itself — run
them in order, read the source, change something, run it again.

```bash
pip install -e .
python examples/tutorial/01_configuration.py
```

## The idea, in one line

**Components carry the weight. Configurations describe it.**

Components are where your logic lives. Configurations are the parameter sets you
run it with — lightweight, numerous, and quick to write, because the normal case
is running many experiments over *the same component*. Almost everything below
follows from that split.

## The steps

| | | Introduces |
|---|---|---|
| 1 | [`01_configuration.py`](01_configuration.py) | `Configuration`, `Param`, validation, why a configuration stays light |
| 2 | [`02_registration.py`](02_registration.py) | components as plain classes, `RegistrationKey`, `Registry.from_key` |
| 3 | [`03_variants.py`](03_variants.py) | **variants** — one component, many configurations |
| 4 | [`04_dependencies.py`](04_dependencies.py) | a configuration that references another, and how sweeps compose |
| 5 | [`05_collections.py`](05_collections.py) | `list` and `dict` of keys |
| 6 | [`06_conditions.py`](06_conditions.py) | conditions, and the valid/invalid split |
| 7 | [`07_project_layout/`](07_project_layout/) | the real directory layout and the CLI |

Steps 1–6 register everything by hand in a single file, so each concept is
readable in one screen. That is a teaching device: real projects use the
directory layout in step 7 and never call `register_configuration` directly.

For the same reason, steps 1–6 bind components with `f"{__name__}.ClassName"`,
which resolves to `__main__` in a script. A real project writes
`"mypackage.components.Tokenizer"`.

## Step 7 — the real thing

```bash
cd examples/tutorial/07_project_layout

cmn-check -dir .          # look for mistakes before running anything
cmn-build -dir .          # resolve, and write the key list to registrations/
cmn-run   -dir .          # pick a configuration interactively and run it
```

`Registry.build` finds every `configurations/` package beneath the directory it
is given, imports the modules, and runs what the `@register` and
`@register_method` decorators buffered. `components/` is a convention, not a
requirement.

Four registrations come out of two declarations, because the strategy declares a
variant and the summariser inherits it:

```
strategy--tags=['truncate']
strategy--tags=['sentences=2', 'truncate']
summariser
summariser--tags=['strategy.sentences=2', 'strategy.truncate']
```

That last key is worth a second look: it records *which* strategy the summariser
was built against. Nobody wrote it down — resolution derived it, and it will be
the same key on the next machine and in six months.

## After the tutorial

- [`../`](..) — a full scikit-learn pipeline: loader, processors, model,
  benchmark. Needs `pip install -e ".[examples]"` and downloads IMDB on first
  run.
- [`../../CONTRIBUTING.md`](../../CONTRIBUTING.md) — the design principle in
  more depth, and how to work on cinnamon itself.

## A note on what is *not* here

`arbitrary_types_allowed`. A configuration that holds a live model or connection
compiles fine and quietly erases the distinction the library is built on, so
cinnamon refuses the field and explains why. Step 1 has a commented-out example
if you want to see the message.
