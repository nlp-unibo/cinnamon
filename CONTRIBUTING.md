# Contributing to cinnamon

## The idea, first

cinnamon separates two things:

- **Components** carry the weight. They are where a program's logic lives, and
  the part meant to be customised.
- **Configurations** describe that weight. They are lightweight, numerous, and
  quick to write, because the normal case is running many experiments over *the
  same component*.

Most of the design follows from that split, and a change that blurs it needs a
good argument. A configuration holds parameters and `RegistrationKey`
references — never a live model, connection, or other domain object.

## Setting up

```bash
git clone git@github.com:nlp-unibo/cinnamon.git
cd cinnamon
python -m venv .venv && source .venv/bin/activate
pip install -e ".[cli,dev]"
```

Optional extras: `examples` (pandas, scikit-learn) to run `examples/`.

## Running the checks

One command, the same checks CI runs:

```bash
nox
```

| Command | What it does |
|---|---|
| `nox` | lint + full test suite on the current interpreter |
| `nox -s lint` | `ruff check`, `ruff format --check`, `mypy` |
| `nox -s tests` | full suite behind the 100% coverage gate |
| `nox -s core` | the suite with the CLI extra *not* installed |
| `nox -s tests -p 3.10` | one specific interpreter |

Plain `pytest` still works for a quick inner loop. `nox` exists so that "is this
green?" is one command rather than four across five environments — CI runs the
full 3.10–3.14 matrix, and you do not need to reproduce that locally.

## The flow

1. **Branch off `main`.** One logical change per branch.
   `feat/…`, `fix/…`, `perf/…`, `docs/…`, `chore/…`.
2. **Work, with tests.** See the invariants below.
3. **`nox`** until green.
4. **Open a pull request.** CI runs the full matrix; the `All checks passed`
   job is the one that gates the merge.
5. **Merge with a fast-forward** (rebase if `main` has moved). History stays
   linear, so `git log --oneline` reads as a list of changes rather than a
   braid.
6. **Delete the branch.**

Direct pushes to `main` are for genuine emergencies. The flow costs a couple of
minutes and has already paid for itself: a bug that 296 passing tests missed was
caught at merge time by running the real command against the real project.

## Invariants CI enforces

**100% statement *and* branch coverage.** Not a vanity number — it is there so
that a line nobody exercises has to be justified out loud, with a
`# pragma: no cover` and a reason. Twice now it has caught a change that looked
safe: an optimisation that broke union dispatch, and a guard removed as "dead"
that was load-bearing.

**`ruff` and `mypy` clean**, with the formatter applied. Markdown is excluded
from the formatter; prose is hand-wrapped.

**3.10 through 3.14.** Genuine differences live in that range — PEP 649
annotations on 3.14, `itertools.batched` from 3.12 — and the library has been
broken by a new release before.

## Writing tests

- **Assert an outcome, not that the code ran.** A test that calls a function and
  checks nothing raises coverage and verifies nothing.
- **Make fakes match the real protocol.** A `Cancel` button that returned its
  label instead of its value once made a broken feature look tested.
- **Add a regression test with every bug fix**, and check it fails against the
  old code before you keep it.
- **Then run the real thing.** The suite is not the last word — several bugs
  here survived a green suite and died the moment someone ran `cmn-check`
  against an actual project.

## Commit messages

A subject line that says what changed, and a body that says why — what the old
behaviour was, what it cost, and what was rejected along the way. The `git log`
of this project is meant to be readable six months later by someone deciding
whether to undo your change.

## Documentation

Public API changes belong in `docsrc/`, built to `docs/` and published by the
`docs.yml` workflow. Anything a user types — a CLI flag, a field type, an
exception they will see — should be documented in the same pull request.
