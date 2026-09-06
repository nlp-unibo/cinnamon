"""
``setup`` -- the entry-point decorator from issue #2.

The issue asked for::

    @Registry.build(directory=Path(...))
    if __name__ == '__main__':
        ....

which is not valid Python: a decorator applies to a ``def`` or a ``class``,
never to a statement. What it was after is clear enough, though -- the four
lines that open every cinnamon script -- so the decorator goes on the entry
point and runs it.

The behaviour that earns the feature is the auto-run. Without it the decorator
would move the ``Registry.build`` call and leave the ``if __name__`` guard
behind, which is one line longer than what it replaces. So the tests below care
most about *when it runs*: as a script, under ``python -m``, and -- the one that
would be a disaster -- not on import.
"""

import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from cinnamon.registry import Registry, setup

PROJECT = Path(__file__).resolve().parent.parent / "examples" / "tutorial"
LAYOUT = PROJECT / "07_project_layout"


PREAMBLE = "from pathlib import Path\n\nfrom cinnamon.registry import Registry, setup\n"


def _script(body: str) -> str:
    return PREAMBLE + body


def _write_entry_point(tmp_path: Path, body: str) -> Path:
    """A real project on disk with a main.py, laid out the documented way."""
    configurations = tmp_path / "configurations"
    components = tmp_path / "components"
    configurations.mkdir()
    components.mkdir()
    (configurations / "__init__.py").write_text("")
    (components / "__init__.py").write_text("")
    (components / "greeter.py").write_text(
        textwrap.dedent("""
            class Greeter:
                def __init__(self, greeting: str):
                    self.greeting = greeting

                def run(self):
                    print(f"greeter says: {self.greeting}")
        """)
    )
    (configurations / "greeter.py").write_text(
        textwrap.dedent("""
            from cinnamon.configuration import Configuration, Param
            from cinnamon.registry import Registry, register


            class GreeterConfig(Configuration):
                greeting: str = Param('hello', description='what to say')


            @register
            def register_greeter():
                Registry.register_configuration(
                    config=GreeterConfig.default(),
                    name='greeter',
                    namespace='demo',
                    component='components.greeter.Greeter',
                )
        """)
    )
    main = tmp_path / "main.py"
    main.write_text(_script(body))
    return main


ENTRY_POINT = """
@setup(directory=Path(__file__).parent, logging_level=None)
def main():
    Registry.instantiate(name='greeter', namespace='demo').run()
"""


def _run(main: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, *args],
        cwd=main.parent,
        capture_output=True,
        text=True,
        timeout=120,
    )


# -- the artefact, run the way a user runs it --


def test_running_the_script_builds_and_runs(tmp_path):
    """`python main.py` -- no `if __name__` guard anywhere in the file."""
    main = _write_entry_point(tmp_path, ENTRY_POINT)

    result = _run(main, "main.py")

    assert result.returncode == 0, result.stderr
    assert "greeter says: hello" in result.stdout
    assert "__main__" not in main.read_text()


def test_running_the_module_builds_and_runs(tmp_path):
    """``python -m main`` sets ``__name__`` to ``__main__`` too."""
    main = _write_entry_point(tmp_path, ENTRY_POINT)

    result = _run(main, "-m", "main")

    assert result.returncode == 0, result.stderr
    assert "greeter says: hello" in result.stdout


def test_importing_the_module_does_not_run_it(tmp_path):
    """The one that would be indefensible.

    Running somebody's entry point as a side effect of importing their module
    would make the decorator unusable in any project with more than one script.
    """
    main = _write_entry_point(tmp_path, ENTRY_POINT)

    result = _run(
        main,
        "-c",
        "import main; print('--- imported ---'); main.main()",
    )

    assert result.returncode == 0, result.stderr
    before, _, after = result.stdout.partition("--- imported ---")
    assert "greeter says" not in before, "the entry point ran on import"
    assert "greeter says: hello" in after, "the function is no longer callable"


# -- the decision itself, in process --


def test_auto_runs_when_defined_in_main(tmp_path, reset_registry, monkeypatch):
    """The auto-run branch, without needing a subprocess to reach it.

    ``__module__`` is what the decorator reads, so setting it is a faithful
    stand-in for the module actually being ``__main__``.
    """
    monkeypatch.chdir(LAYOUT)
    calls = []

    def entry_point():
        calls.append(Registry.expanded)

    entry_point.__module__ = "__main__"

    setup(logging_level=None)(entry_point)

    assert calls == [True], "the entry point did not run, or ran before the build"


def test_does_not_auto_run_when_imported(tmp_path, reset_registry, monkeypatch):
    monkeypatch.chdir(LAYOUT)
    calls = []

    def entry_point():
        calls.append(1)

    decorated = setup(logging_level=None)(entry_point)

    assert calls == []
    decorated()
    assert calls == [1]


def test_directory_defaults_to_the_working_directory(reset_registry, monkeypatch):
    """No ``directory`` means the working directory, as ``-dir`` does."""
    monkeypatch.chdir(LAYOUT)
    seen = {}

    @setup(logging_level=None)
    def entry_point():
        seen["keys"] = Registry.retrieve_keys()

    entry_point()

    assert len(seen["keys"]) == 4


def test_configures_logging_by_default(tmp_path, reset_registry, monkeypatch):
    """The fourth line of the boilerplate is ``logging.basicConfig``."""
    monkeypatch.chdir(LAYOUT)
    levels = []

    import logging

    monkeypatch.setattr(
        logging, "basicConfig", lambda **kwargs: levels.append(kwargs.get("level"))
    )

    @setup()
    def entry_point():
        pass

    entry_point()

    assert levels == [logging.INFO]


def test_logging_can_be_left_alone(tmp_path, reset_registry, monkeypatch):
    """``logging_level=None`` for a script that configures its own."""
    monkeypatch.chdir(LAYOUT)
    called = []

    import logging

    monkeypatch.setattr(logging, "basicConfig", lambda **kwargs: called.append(kwargs))

    @setup(logging_level=None)
    def entry_point():
        pass

    entry_point()

    assert called == []


def test_arguments_and_return_value_pass_through(reset_registry, monkeypatch):
    monkeypatch.chdir(LAYOUT)

    @setup(logging_level=None)
    def entry_point(a, b=2):
        return a + b

    assert entry_point(1) == 3
    assert entry_point(1, b=10) == 11


def test_keeps_the_wrapped_function_identity(reset_registry):
    @setup(logging_level=None)
    def entry_point():
        """A docstring worth keeping."""

    assert entry_point.__name__ == "entry_point"
    assert entry_point.__doc__ == "A docstring worth keeping."


def test_a_missing_directory_is_refused(reset_registry, tmp_path):
    """``check_directory`` is reused, so the error matches the CLI's."""

    @setup(directory=tmp_path / "nope", logging_level=None)
    def entry_point():
        pass  # pragma: no cover

    with pytest.raises(FileNotFoundError):
        entry_point()
