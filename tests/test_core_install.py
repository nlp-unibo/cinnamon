"""
The commands that do not prompt must work without the optional CLI extra.

``cmn-build`` and ``cmn-check`` are non-interactive, and ``cmn-check`` exists to
gate a commit or a CI job -- neither has any business requiring a terminal-prompt
library. They nevertheless failed on a core install with a raw
``ModuleNotFoundError``, because ``cli.py`` imported ``cinnamon.utility.inquirer``
at module scope and *that* imports InquirerPy at module scope. The careful
``_require_inquirer`` guard, written to produce a helpful message, was
unreachable: the import blew up three lines into the module.

Nothing caught it. The core CI job installs without the extra but skips
``test_cli.py`` -- correctly, since those tests need InquirerPy -- so no test in
that job ever imported ``cinnamon.cli`` at all. The gap was not a missing
assertion, it was that the artefact was never run.

These tests state the invariant directly, in a subprocess, so they hold in the
full environment too: importing the CLI must not drag in the extra, and the
commands that do need it must say so.
"""

import subprocess
import sys
import textwrap


def _run(code: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-c", textwrap.dedent(code)],
        capture_output=True,
        text=True,
    )


def test_importing_the_cli_does_not_import_the_optional_extra():
    """The invariant, stated as directly as it can be.

    A fresh interpreter, so it is unaffected by whatever the test session has
    already imported. This fails against the old ``cli.py`` even with InquirerPy
    installed, which is what makes it a useful regression test rather than one
    that only fires in a core environment.
    """
    result = _run("""
        import sys

        import cinnamon.cli

        assert "InquirerPy" not in sys.modules, sorted(
            name for name in sys.modules if "nquirer" in name
        )
        print("clean")
    """)

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "clean"


def test_non_interactive_commands_run_without_inquirerpy(tmp_path, monkeypatch):
    """``cmn-check`` end to end with InquirerPy made unimportable.

    Blocking the module rather than uninstalling it: the failure mode is an
    import, so refusing the import reproduces it exactly.
    """
    project = tmp_path / "project"
    configurations = project / "configurations"
    configurations.mkdir(parents=True)
    (configurations / "__init__.py").write_text("")
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
                    namespace='testing',
                )
        """)
    )

    result = _run(f"""
        import sys

        class Blocked:
            def find_module(self, name, path=None):
                return self.find_spec(name, path)

            def find_spec(self, name, path=None, target=None):
                if name.split(".")[0] == "InquirerPy":
                    raise ImportError("No module named 'InquirerPy'")
                return None

        sys.meta_path.insert(0, Blocked())
        sys.argv = ["cmn-check", "-dir", {str(project)!r}]

        from cinnamon.cli import check

        check()
    """)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "No registration key problems found." in result.stdout
