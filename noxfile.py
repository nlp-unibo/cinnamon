"""
Local reproduction of the CI pipeline.

``nox`` with no arguments runs the same checks CI does, on whichever interpreter
you invoked it with. That is the point of the file: "is this green?" should be
one command, not four commands across five virtual environments.

    nox                     lint + full test suite, current interpreter
    nox -s lint             ruff check, ruff format --check, mypy
    nox -s tests            full suite behind the 100% coverage gate
    nox -s core             the suite without the CLI extra installed
    nox -s examples         the shipped examples, with pandas and scikit-learn
    nox -s tests -p 3.10    a specific interpreter

CI runs ``tests`` and ``core`` across 3.10-3.14. Missing interpreters are
skipped rather than failing, so a machine with one Python still gets a useful
answer -- the matrix is CI's job.
"""

import nox

PYTHON_VERSIONS = ["3.10", "3.11", "3.12", "3.13", "3.14"]
LINT_VERSION = "3.12"

# uv when it is available, virtualenv otherwise: the former makes a five-version
# matrix quick enough to actually run before pushing.
nox.options.default_venv_backend = "uv|virtualenv"
nox.options.error_on_missing_interpreters = False
nox.options.sessions = ["lint", "tests"]

#: The examples pull in pandas and scikit-learn. They do not vary by interpreter,
#: so verifying them once is enough.
EXAMPLES_VERSION = "3.12"


@nox.session(python=LINT_VERSION)
def lint(session: nox.Session) -> None:
    """Style, imports, formatting and types."""
    session.install("-e", ".[cli,dev]")
    session.run("ruff", "check", ".")
    session.run("ruff", "format", "--check", ".")
    session.run("mypy", "cinnamon")


@nox.session(python=PYTHON_VERSIONS)
def tests(session: nox.Session) -> None:
    """The full suite, behind the coverage gate CI enforces."""
    session.install("-e", ".[cli,dev]")
    session.run("pytest", "--cov-fail-under=100", "--cov-report=term-missing")


@nox.session(python=PYTHON_VERSIONS)
def core(session: nox.Session) -> None:
    """The suite without InquirerPy, proving the library works without the extra.

    No coverage gate here: cli.py and inquirer.py cannot run without the CLI
    extra, so a whole-package percentage would be measuring their absence.
    """
    session.install("-e", ".[dev]")
    session.run(
        "pytest",
        "--no-cov",
        "--ignore=tests/test_cli.py",
        "--ignore=tests/test_inquirer.py",
    )


@nox.session(python=EXAMPLES_VERSION)
def examples(session: nox.Session) -> None:
    """The shipped examples, including the ones needing pandas and scikit-learn.

    Separate from `tests` because those dependencies are heavy and the examples
    do not behave differently per interpreter. Without this the binding check
    for the scikit-learn pipeline silently skips, which is how its demos came to
    be broken for months.
    """
    session.install("-e", ".[cli,dev,examples]")
    session.run("pytest", "tests/test_examples.py", "--no-cov", "-v")
