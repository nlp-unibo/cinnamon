.. _contributing:

Contributing
*********************************************

The same guide that ships as ``CONTRIBUTING.md`` in the repository, so that a
reader of this site does not have to leave it.

=============================================
The idea, first
=============================================

cinnamon separates two things.

- **Components** carry the weight. They are where a program's logic lives, and
  the part meant to be customised.
- **Configurations** describe that weight. They are lightweight, numerous, and
  quick to write, because the normal case is running many experiments over *the
  same component*.

Most of the design follows from that split, and a change that blurs it needs a
good argument. A configuration holds parameters and ``RegistrationKey``
references, never a live model, connection, or other domain object.

=============================================
Setting up
=============================================

.. code-block:: bash

    git clone git@github.com:nlp-unibo/cinnamon.git
    cd cinnamon
    python -m venv .venv && source .venv/bin/activate
    pip install -e ".[cli,dev]"

Optional extras: ``examples`` (pandas, scikit-learn) to run ``examples/``, and
``docs`` (Sphinx, the theme, mermaid) to build this site.

=============================================
Running the checks
=============================================

One command, the same checks CI runs:

.. code-block:: bash

    nox

.. list-table::
    :header-rows: 1
    :widths: 35 65

    * - Command
      - What it does
    * - ``nox``
      - lint plus the full test suite on the current interpreter
    * - ``nox -s lint``
      - ``ruff check``, ``ruff format --check``, ``mypy``
    * - ``nox -s tests``
      - the full suite behind the 100% coverage gate
    * - ``nox -s core``
      - the suite with the CLI extra *not* installed
    * - ``nox -s docs``
      - this documentation, warnings treated as errors
    * - ``nox -s tests -p 3.10``
      - one specific interpreter

Plain ``pytest`` still works for a quick inner loop. ``nox`` exists so that "is
this green?" is one command rather than four across five environments. CI runs
the full 3.10 to 3.14 matrix, and you do not need to reproduce that locally.

=============================================
The flow
=============================================

1. **Branch off** ``main``. One logical change per branch: ``feat/…``,
   ``fix/…``, ``perf/…``, ``docs/…``, ``chore/…``.
2. **Work, with tests.** See the invariants below.
3. Run ``nox`` until green.
4. **Open a pull request.** CI runs the full matrix, and the ``All checks
   passed`` job is the one that gates the merge.
5. **Merge with a fast-forward**, rebasing if ``main`` has moved. History stays
   linear, so ``git log --oneline`` reads as a list of changes rather than a
   braid.
6. **Delete the branch.**

Direct pushes to ``main`` are for genuine emergencies. The flow costs a couple
of minutes and has already paid for itself: a bug that 296 passing tests missed
was caught at merge time by running the real command against a real project.

=============================================
Invariants CI enforces
=============================================

**100% statement and branch coverage.** Not a vanity number. It is there so
that a line nobody exercises has to be justified out loud, with a
``# pragma: no cover`` and a reason. Twice now it has caught a change that
looked safe: an optimisation that broke union dispatch, and a guard removed as
"dead" that was load-bearing.

**ruff and mypy clean**, with the formatter applied. Markdown is excluded from
the formatter, because prose is hand-wrapped.

**3.10 through 3.14.** Genuine differences live in that range, such as PEP 649
annotations on 3.14 and ``itertools.batched`` from 3.12, and the library has
been broken by a new release before.

=============================================
Writing tests
=============================================

- **Assert an outcome, not that the code ran.** A test that calls a function and
  checks nothing raises coverage and verifies nothing.
- **Make fakes match the real protocol.** A ``Cancel`` button that returned its
  label instead of its value once made a broken feature look tested.
- **Add a regression test with every bug fix**, and check that it fails against
  the old code before you keep it.
- **Then run the real thing.** The suite is not the last word. Several bugs here
  survived a green suite and died the moment someone ran ``cmn-check`` against
  an actual project.
- **Before tagging a release, run a downstream project's suite against the
  branch.** 2.1.2 shipped on 557 passing tests at 100% branch coverage and broke
  pyhighlights in 49 of them: it forgot the caller's own imports, so a second
  build handed back a second copy of every class. Coverage measures lines, not
  *arrangements*, and the arrangement that broke, a caller importing from a
  directory it then scans, is not one this project builds for itself. The check
  is two commands, run in the downstream checkout:

  .. code-block:: bash

      uv pip install -e ../cinnamon && uv run pytest

  CI runs this for you on any pull request touching ``cinnamon/`` or
  ``pyproject.toml``, in ``.github/workflows/downstream.yml``. It is not part of
  ``all-green``, because that job counts a skipped dependency as a failure and
  this one is skipped on a documentation-only pull request. Read it before
  tagging: a red ``Downstream`` is a release that must not go out, whatever this
  repository's own matrix says.

=============================================
Commit messages
=============================================

A subject line that says what changed, and a body that says why: what the old
behaviour was, what it cost, and what was rejected along the way. The ``git
log`` of this project is meant to be readable six months later by someone
deciding whether to undo your change.

=============================================
Documentation
=============================================

Public API changes belong in ``docsrc/``. Anything a user types, such as a CLI
flag, a field type, or an exception they will see, should be documented in the
same pull request.

``nox -s docs`` builds the site into ``docsrc/build/html`` with warnings treated
as errors, and the ``docs.yml`` workflow publishes that build to GitHub Pages. A
page that moves keeps its old URL alive with a stub under
``docsrc/source/_redirects``: GitHub Pages serves static files and cannot issue
a redirect, so a zero-delay meta refresh is the mechanism available.
