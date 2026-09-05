"""
CLI (cinnamon/cli.py) tests.

The CLI is argparse + thin Registry wrappers; the interactive
`cmn-run`/`cmn-generate` flows are exercised with stubbed Registry and
InquirerPy objects so no terminal is ever touched.
"""

import json
import sys
from pathlib import Path

import pytest

import cinnamon.cli as cli
from cinnamon.configuration import Configuration
from cinnamon.registry import ConfigurationInfo, RegistrationKey

# -- _require_inquirer --


def test_require_inquirer_raises_import_error(monkeypatch):
    monkeypatch.setitem(sys.modules, "InquirerPy", None)
    with pytest.raises(ImportError, match="cinnamon\\[cli\\]"):
        cli._require_inquirer()


# -- build --


def test_cli_build_reaches_registry_build(tmp_path, monkeypatch, reset_registry):
    """
    build() with a valid -dir calls Registry.build and writes the two JSON
    registrations files. RegistrationKey is serialized via its str() form
    (round-trippable through RegistrationKey.from_string).
    """
    called = {}
    key = RegistrationKey(name="test", tags={"t1"}, namespace="testing")

    def fake_build(directory, external_directories=None):
        called["directory"] = directory
        called["external_directories"] = external_directories
        return {key}, set()

    monkeypatch.setattr("sys.argv", ["cmn-build", "-dir", str(tmp_path)])
    monkeypatch.setattr(cli.Registry, "build", fake_build)

    cli.build()

    assert called["directory"] == tmp_path.resolve()
    assert called["external_directories"] is None

    valid_file = tmp_path / "registrations" / "valid_keys.json"
    invalid_file = tmp_path / "registrations" / "invalid_keys.json"
    assert valid_file.exists()
    assert invalid_file.exists()

    valid_str = json.loads(valid_file.read_text())
    assert valid_str == [str(key)]
    # round-trips back to a RegistrationKey
    assert RegistrationKey.from_string(valid_str[0]) == key
    assert json.loads(invalid_file.read_text()) == []


def test_cli_build_with_invalid_keys(tmp_path, monkeypatch, reset_registry):
    """Invalid keys are still logged and written out."""
    called = {}
    valid_key = RegistrationKey(name="ok", namespace="testing")
    invalid_key = RegistrationKey(name="bad", namespace="testing")

    def fake_build(directory, external_directories=None):
        called["directory"] = directory
        return {valid_key}, {invalid_key}

    monkeypatch.setattr("sys.argv", ["cmn-build", "-dir", str(tmp_path)])
    monkeypatch.setattr(cli.Registry, "build", fake_build)

    cli.build()

    valid_file = tmp_path / "registrations" / "valid_keys.json"
    invalid_file = tmp_path / "registrations" / "invalid_keys.json"
    assert json.loads(valid_file.read_text()) == [str(valid_key)]
    assert json.loads(invalid_file.read_text()) == [str(invalid_key)]


def test_cli_build_nonexistent_directory_raises(monkeypatch, reset_registry):
    monkeypatch.setattr(
        "sys.argv", ["cmn-build", "-dir", str(Path("/nonexistent/cinnamon-dir"))]
    )
    with pytest.raises(FileNotFoundError):
        cli.build()


def test_cli_build_bad_external_path_typeerror(tmp_path, monkeypatch, reset_registry):
    """-ext pointing to a non-.json file triggers TypeError via sanity check."""
    ext_file = tmp_path / "externals.txt"
    ext_file.write_text("[]")

    monkeypatch.setattr(
        "sys.argv", ["cmn-build", "-dir", str(tmp_path), "-ext", str(ext_file)]
    )
    with pytest.raises(TypeError):
        cli.build()


# -- run --


class _FakeConfirm:
    def __init__(self, value):
        self._value = value

    def execute(self):
        return self._value


class _FakeInquirerCLI:
    def confirm(self, **kwargs):
        return _FakeConfirm(True)


class _FakeComponent:
    def __init__(self, folder_name=None, batch_size=None):
        self.folder_name = folder_name
        self.batch_size = batch_size
        self.run_calls = 0

    def run(self):
        self.run_calls += 1
        return "ran"


def test_cli_run_no_runnable_keys_aborts(tmp_path, monkeypatch, reset_registry):
    """
    run() with no runnable keys logs 'Could not find any registered runnable
     component' and returns without prompting.
    """
    monkeypatch.setattr("sys.argv", ["cmn-run", "-dir", str(tmp_path)])
    monkeypatch.setattr(
        cli.Registry, "build", lambda directory, external_directories=None: None
    )
    monkeypatch.setattr(cli.Registry, "retrieve_runnable_keys", lambda: [])

    prompted = []
    monkeypatch.setattr(cli, "filter_keys", lambda keys: prompted.append(keys) or [])

    cli.run()

    assert prompted == []  # aborted before reaching the prompt


def test_cli_run_with_external_path(tmp_path, monkeypatch, reset_registry):
    """run() accepts -ext and loads the external JSON before building."""
    ext = tmp_path / "externals.json"
    ext.write_text(json.dumps([str(tmp_path)]))

    monkeypatch.setattr(
        "sys.argv", ["cmn-run", "-dir", str(tmp_path), "-ext", str(ext)]
    )

    called = {}

    def fake_build(directory, external_directories=None):
        called["external_directories"] = external_directories

    monkeypatch.setattr(cli.Registry, "build", fake_build)
    monkeypatch.setattr(cli.Registry, "retrieve_runnable_keys", lambda: [])

    cli.run()

    assert called["external_directories"] == [str(tmp_path)]


def test_cli_run_executes_components(tmp_path, monkeypatch, reset_registry):
    """run() builds registry, prompts, then runs the selected component."""
    key = RegistrationKey(name="exp", namespace="testing")

    monkeypatch.setattr("sys.argv", ["cmn-run", "-dir", str(tmp_path)])
    monkeypatch.setattr(
        cli.Registry, "build", lambda directory, external_directories=None: None
    )
    monkeypatch.setattr(cli.Registry, "retrieve_runnable_keys", lambda: [key])
    monkeypatch.setattr(cli, "filter_keys", lambda keys: [key])
    monkeypatch.setattr(cli, "_require_inquirer", lambda: _FakeInquirerCLI())
    monkeypatch.setattr(
        cli.Registry,
        "retrieve_configuration_info",
        lambda registration_key: ConfigurationInfo(
            config=Configuration.default(), run_method="run"
        ),
    )
    component = _FakeComponent()
    monkeypatch.setattr(
        cli.Registry, "from_key", lambda registration_key, **kwargs: component
    )

    cli.run()

    assert component.run_calls == 1


def test_cli_run_missing_run_method_raises(tmp_path, monkeypatch, reset_registry):
    """run() raises RuntimeError when the bound component lacks run_method."""
    key = RegistrationKey(name="exp", namespace="testing")

    monkeypatch.setattr("sys.argv", ["cmn-run", "-dir", str(tmp_path)])
    monkeypatch.setattr(
        cli.Registry, "build", lambda directory, external_directories=None: None
    )
    monkeypatch.setattr(cli.Registry, "retrieve_runnable_keys", lambda: [key])
    monkeypatch.setattr(cli, "filter_keys", lambda keys: [key])
    monkeypatch.setattr(cli, "_require_inquirer", lambda: _FakeInquirerCLI())
    monkeypatch.setattr(
        cli.Registry,
        "retrieve_configuration_info",
        lambda registration_key: ConfigurationInfo(
            config=Configuration.default(), run_method="run"
        ),
    )
    monkeypatch.setattr(
        cli.Registry, "from_key", lambda registration_key, **kwargs: object()
    )

    with pytest.raises(RuntimeError, match="has no method"):
        cli.run()


def test_cli_run_confirm_false_aborts(tmp_path, monkeypatch, reset_registry):
    """run() returns without executing when the user declines confirmation."""
    key = RegistrationKey(name="exp", namespace="testing")

    class _FakeConfirmFalse:
        def execute(self):
            return False

    class _FakeInquirerCLIFalse:
        def confirm(self, **kwargs):
            return _FakeConfirmFalse()

    monkeypatch.setattr("sys.argv", ["cmn-run", "-dir", str(tmp_path)])
    monkeypatch.setattr(
        cli.Registry, "build", lambda directory, external_directories=None: None
    )
    monkeypatch.setattr(cli.Registry, "retrieve_runnable_keys", lambda: [key])
    monkeypatch.setattr(cli, "filter_keys", lambda keys: [key])
    monkeypatch.setattr(cli, "_require_inquirer", lambda: _FakeInquirerCLIFalse())

    component = _FakeComponent()
    monkeypatch.setattr(
        cli.Registry,
        "retrieve_configuration_info",
        lambda registration_key: ConfigurationInfo(
            config=Configuration.default(), run_method="run"
        ),
    )
    monkeypatch.setattr(
        cli.Registry, "from_key", lambda registration_key, **kwargs: component
    )

    cli.run()

    assert component.run_calls == 0


# -- generate --


def test_cli_generate_writes_script(tmp_path, monkeypatch, reset_registry):
    """
    generate() with stubbed Registry/filter_keys writes the experiment script
     to the run directory.
    """
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    key = RegistrationKey(name="exp", namespace="cli")

    monkeypatch.setattr(
        "sys.argv",
        [
            "cmn-generate",
            "-dir",
            str(tmp_path),
            "-run-dir",
            str(run_dir),
            "-name",
            "myexp",
        ],
    )
    monkeypatch.setattr(cli, "_require_inquirer", lambda: _FakeInquirerCLI())
    monkeypatch.setattr(cli, "filter_keys", lambda keys: list(keys))
    monkeypatch.setattr(
        cli.Registry,
        "build",
        lambda directory, external_directories=None: ({key}, set()),
    )

    cli.generate()

    script = run_dir / "myexp.py"
    assert script.exists()
    content = script.read_text()
    assert "name=exp" in content


def test_cli_generate_template_is_valid_python(tmp_path, monkeypatch, reset_registry):
    """
    The generated script body must be syntactically valid Python. This guards
     the `generate()` template paren bug (Path(...) missing a closing paren).
    """
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    key = RegistrationKey(name="exp", namespace="cli")

    monkeypatch.setattr(
        "sys.argv",
        [
            "cmn-generate",
            "-dir",
            str(tmp_path),
            "-run-dir",
            str(run_dir),
            "-name",
            "myexp",
        ],
    )
    monkeypatch.setattr(cli, "_require_inquirer", lambda: _FakeInquirerCLI())
    monkeypatch.setattr(cli, "filter_keys", lambda keys: list(keys))
    monkeypatch.setattr(
        cli.Registry,
        "build",
        lambda directory, external_directories=None: ({key}, set()),
    )

    cli.generate()

    # compile() raises SyntaxError if the generated body is malformed
    code = (run_dir / "myexp.py").read_text()
    compile(code, "<generated>", "exec")
    assert str(key) in code


def test_cli_generate_no_valid_keys_aborts(tmp_path, monkeypatch, reset_registry):
    """generate() with no valid runnable keys returns early."""
    run_dir = tmp_path / "run"
    run_dir.mkdir()

    monkeypatch.setattr(
        "sys.argv",
        [
            "cmn-generate",
            "-dir",
            str(tmp_path),
            "-run-dir",
            str(run_dir),
            "-name",
            "myexp",
        ],
    )
    monkeypatch.setattr(cli, "_require_inquirer", lambda: _FakeInquirerCLI())
    monkeypatch.setattr(
        cli.Registry,
        "build",
        lambda directory, external_directories=None: (set(), set()),
    )

    cli.generate()

    assert not (run_dir / "myexp.py").exists()


def test_cli_generate_with_external_path(tmp_path, monkeypatch, reset_registry):
    """generate() accepts -ext and passes the parsed list to the template."""
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    ext = tmp_path / "externals.json"
    ext.write_text(json.dumps([str(tmp_path)]))
    key = RegistrationKey(name="exp", namespace="cli")

    monkeypatch.setattr(
        "sys.argv",
        [
            "cmn-generate",
            "-dir",
            str(tmp_path),
            "-run-dir",
            str(run_dir),
            "-name",
            "myexp",
            "-ext",
            str(ext),
        ],
    )
    monkeypatch.setattr(cli, "_require_inquirer", lambda: _FakeInquirerCLI())
    monkeypatch.setattr(cli, "filter_keys", lambda keys: list(keys))
    monkeypatch.setattr(
        cli.Registry,
        "build",
        lambda directory, external_directories=None: ({key}, set()),
    )

    cli.generate()

    script = (run_dir / "myexp.py").read_text()
    assert "name=exp" in script


def test_cli_generate_confirm_false_aborts(tmp_path, monkeypatch, reset_registry):
    """generate() returns without writing when user declines."""

    class _FakeConfirmFalse:
        def execute(self):
            return False

    class _FakeInquirerCLIFalse:
        def confirm(self, **kwargs):
            return _FakeConfirmFalse()

    run_dir = tmp_path / "run"
    run_dir.mkdir()
    key = RegistrationKey(name="exp", namespace="cli")

    monkeypatch.setattr(
        "sys.argv",
        [
            "cmn-generate",
            "-dir",
            str(tmp_path),
            "-run-dir",
            str(run_dir),
            "-name",
            "myexp",
        ],
    )
    monkeypatch.setattr(cli, "_require_inquirer", lambda: _FakeInquirerCLIFalse())
    monkeypatch.setattr(cli, "filter_keys", lambda keys: list(keys))
    monkeypatch.setattr(
        cli.Registry,
        "build",
        lambda directory, external_directories=None: ({key}, set()),
    )

    cli.generate()

    assert not (run_dir / "myexp.py").exists()


def test_cli_generate_overwrite_prompt(tmp_path, monkeypatch, reset_registry):
    """generate() overwrites an existing script when user answers y."""
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    key = RegistrationKey(name="exp", namespace="cli")
    script = run_dir / "myexp.py"
    script.write_text("old")

    responses = {"first": "y"}

    def fake_input(prompt):
        return responses.pop("first", "n")

    monkeypatch.setattr("builtins.input", fake_input)
    monkeypatch.setattr(
        "sys.argv",
        [
            "cmn-generate",
            "-dir",
            str(tmp_path),
            "-run-dir",
            str(run_dir),
            "-name",
            "myexp",
        ],
    )
    monkeypatch.setattr(cli, "_require_inquirer", lambda: _FakeInquirerCLI())
    monkeypatch.setattr(cli, "filter_keys", lambda keys: list(keys))
    monkeypatch.setattr(
        cli.Registry,
        "build",
        lambda directory, external_directories=None: ({key}, set()),
    )

    cli.generate()

    assert script.exists()
    assert "name=exp" in script.read_text()


def test_cli_generate_overwrite_abort(tmp_path, monkeypatch, reset_registry):
    """generate() aborts when user answers n to overwrite prompt."""
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    key = RegistrationKey(name="exp", namespace="cli")
    script = run_dir / "myexp.py"
    script.write_text("old")

    responses = {"first": "n"}

    def fake_input(prompt):
        return responses.pop("first", "n")

    monkeypatch.setattr("builtins.input", fake_input)
    monkeypatch.setattr(
        "sys.argv",
        [
            "cmn-generate",
            "-dir",
            str(tmp_path),
            "-run-dir",
            str(run_dir),
            "-name",
            "myexp",
        ],
    )
    monkeypatch.setattr(cli, "_require_inquirer", lambda: _FakeInquirerCLI())
    monkeypatch.setattr(cli, "filter_keys", lambda keys: list(keys))
    monkeypatch.setattr(
        cli.Registry,
        "build",
        lambda directory, external_directories=None: ({key}, set()),
    )

    cli.generate()

    assert script.read_text() == "old"


# -- selection prompt loop --


def test_prompt_for_keys_retries_when_filters_match_nothing(monkeypatch):
    """An empty match re-opens the prompt; a later non-empty result is returned."""
    key = RegistrationKey(name="exp", namespace="testing")
    results = [[], [key]]
    monkeypatch.setattr(cli, "filter_keys", lambda keys: results.pop(0))

    assert cli._prompt_for_keys([key]) == [key]
    assert results == []  # both prompts consumed


def test_prompt_for_keys_stops_on_cancel(monkeypatch):
    """Cancelling returns no keys instead of re-prompting forever."""
    key = RegistrationKey(name="exp", namespace="testing")
    calls = []

    def fake_filter(keys):
        calls.append(keys)
        return None

    monkeypatch.setattr(cli, "filter_keys", fake_filter)

    assert cli._prompt_for_keys([key]) == []
    assert len(calls) == 1  # cancelled, not retried


def test_cli_run_aborts_when_selection_cancelled(tmp_path, monkeypatch, reset_registry):
    """run() executes nothing when the user cancels at the key prompt."""
    key = RegistrationKey(name="exp", namespace="testing")
    component = _FakeComponent()

    monkeypatch.setattr("sys.argv", ["cmn-run", "-dir", str(tmp_path)])
    monkeypatch.setattr(
        cli.Registry, "build", lambda directory, external_directories=None: None
    )
    monkeypatch.setattr(cli.Registry, "retrieve_runnable_keys", lambda: [key])
    monkeypatch.setattr(cli, "filter_keys", lambda keys: None)
    monkeypatch.setattr(cli, "_require_inquirer", lambda: _FakeInquirerCLI())
    monkeypatch.setattr(
        cli.Registry, "from_key", lambda registration_key, **kwargs: component
    )

    cli.run()

    assert component.run_calls == 0


def test_cli_generate_aborts_when_selection_cancelled(
    tmp_path, monkeypatch, reset_registry
):
    """generate() writes no script when the user cancels at the key prompt."""
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    key = RegistrationKey(name="exp", namespace="cli")

    monkeypatch.setattr(
        "sys.argv",
        [
            "cmn-generate",
            "-dir",
            str(tmp_path),
            "-run-dir",
            str(run_dir),
            "-name",
            "myexp",
        ],
    )
    monkeypatch.setattr(cli, "_require_inquirer", lambda: _FakeInquirerCLI())
    monkeypatch.setattr(cli, "filter_keys", lambda keys: None)
    monkeypatch.setattr(
        cli.Registry,
        "build",
        lambda directory, external_directories=None: ({key}, set()),
    )

    cli.generate()

    assert not (run_dir / "myexp.py").exists()


def test_cli_build_reuses_existing_registrations_directory(
    tmp_path, monkeypatch, reset_registry
):
    """Re-running build() over an existing registrations/ folder overwrites it."""
    registrations = tmp_path / "registrations"
    registrations.mkdir()
    (registrations / "valid_keys.json").write_text('["stale"]')
    key = RegistrationKey(name="fresh", namespace="testing")

    monkeypatch.setattr("sys.argv", ["cmn-build", "-dir", str(tmp_path)])
    monkeypatch.setattr(
        cli.Registry,
        "build",
        lambda directory, external_directories=None: ({key}, set()),
    )

    cli.build()

    assert json.loads((registrations / "valid_keys.json").read_text()) == [str(key)]


# -- check --


def _write_project(tmp_path, body):
    configurations = tmp_path / "configurations"
    configurations.mkdir()
    (configurations / "regs.py").write_text(body)
    return tmp_path


CLEAN_PROJECT = """
from cinnamon.configuration import Configuration
from cinnamon.registry import RegistrationKey, Registry, register

class Leaf(Configuration):
    x: int = 1

@register
def registrations():
    Registry.register_configuration(Leaf(), name="tokenizer", namespace="nlp")
"""

BROKEN_PROJECT = """
from cinnamon.configuration import Configuration
from cinnamon.registry import RegistrationKey, Registry, register

class Leaf(Configuration):
    x: int = 1

class Pipeline(Configuration):
    tok: RegistrationKey = RegistrationKey(name="tokeniser", namespace="nlp")

@register
def registrations():
    Registry.register_configuration(Leaf(), name="tokenizer", namespace="nlp")
    Registry.register_configuration(Pipeline(), name="pipeline", namespace="nlp")
"""

WARNING_PROJECT = """
from cinnamon.configuration import Configuration
from cinnamon.registry import Registry, register

class Leaf(Configuration):
    x: int = 1

@register
def registrations():
    Registry.register_configuration(Leaf(), name="a", tags={"imdb"}, namespace="nlp")
    Registry.register_configuration(Leaf(), name="b", tags={"IMDB"}, namespace="nlp")
"""


def test_cli_check_passes_on_a_clean_project(
    tmp_path, monkeypatch, capsys, reset_registry
):
    """A resolvable project reports nothing and exits normally."""
    project = _write_project(tmp_path, CLEAN_PROJECT)
    monkeypatch.setattr("sys.argv", ["cmn-check", "-dir", str(project)])

    cli.check()

    assert "No registration key problems found." in capsys.readouterr().out


def test_cli_check_reports_broken_references_and_exits_nonzero(
    tmp_path, monkeypatch, capsys, reset_registry
):
    """A broken reference is an error: reported with a suggestion, exit code 1."""
    project = _write_project(tmp_path, BROKEN_PROJECT)
    monkeypatch.setattr("sys.argv", ["cmn-check", "-dir", str(project)])

    with pytest.raises(SystemExit) as raised:
        cli.check()

    assert raised.value.code == 1
    output = capsys.readouterr().out
    assert "[error] unresolved-key" in output
    assert "name 'tokeniser' -> 'tokenizer'" in output
    # the binding pass is skipped, since it needs a registry that resolves
    assert "skipping the binding analysis" in output


def test_cli_check_warnings_do_not_fail_by_default(
    tmp_path, monkeypatch, capsys, reset_registry
):
    project = _write_project(tmp_path, WARNING_PROJECT)
    monkeypatch.setattr("sys.argv", ["cmn-check", "-dir", str(project)])

    cli.check()

    assert "[warning] near-duplicate-tag" in capsys.readouterr().out


def test_cli_check_strict_fails_on_warnings(
    tmp_path, monkeypatch, capsys, reset_registry
):
    project = _write_project(tmp_path, WARNING_PROJECT)
    monkeypatch.setattr("sys.argv", ["cmn-check", "-dir", str(project), "--strict"])

    with pytest.raises(SystemExit) as raised:
        cli.check()

    assert raised.value.code == 1


def test_cli_check_fails_on_binding_errors(
    tmp_path, monkeypatch, capsys, reset_registry
):
    """Keys may resolve while a component path does not import."""
    project = _write_project(
        tmp_path,
        CLEAN_PROJECT.replace(
            'name="tokenizer", namespace="nlp")',
            'name="tokenizer", namespace="nlp", component="nope.Missing")',
        ),
    )
    monkeypatch.setattr("sys.argv", ["cmn-check", "-dir", str(project)])

    with pytest.raises(SystemExit) as raised:
        cli.check()

    assert raised.value.code == 1
    assert "cannot be imported" in capsys.readouterr().out
