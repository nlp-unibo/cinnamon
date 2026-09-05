"""
The shipped examples have to keep working.

Both demos under ``examples/demos`` were broken for some time: they called
``SomeComponent.instantiate(key)``, a classmethod that disappeared with the
``Component`` base class. Nothing noticed, because nothing ran them. These tests
exist so that cannot happen twice.

The tutorial steps are executed for real. The scikit-learn pipeline under
``examples/`` is not -- it downloads a dataset -- so it is checked as far as it
can be without running: it must build, and its components must import and match
their configurations.
"""

import re
import subprocess
import sys
from pathlib import Path

import pytest

from cinnamon.registry import Registry
from cinnamon.utility.static_analyzer import analyze_registry

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
TUTORIAL = EXAMPLES / "tutorial"

TUTORIAL_STEPS = sorted(path.name for path in TUTORIAL.glob("0*.py") if path.is_file())


def test_the_tutorial_steps_are_all_present():
    """A renamed or dropped step should fail loudly, not silently stop running."""
    assert TUTORIAL_STEPS == [
        "01_configuration.py",
        "02_registration.py",
        "03_variants.py",
        "04_dependencies.py",
        "05_collections.py",
        "06_conditions.py",
    ]


@pytest.mark.parametrize("step", TUTORIAL_STEPS)
def test_tutorial_step_runs(step):
    """Every step executes cleanly, in a fresh process, with no arguments."""
    result = subprocess.run(
        [sys.executable, str(TUTORIAL / step)],
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert result.returncode == 0, f"{step} failed:\n{result.stderr}"
    assert result.stdout.strip(), f"{step} printed nothing"


def test_tutorial_project_layout_builds(reset_registry):
    """Step 7 is a real project: it must build through the ordinary entry point."""
    valid_keys, invalid_keys = Registry.build(directory=TUTORIAL / "07_project_layout")

    assert invalid_keys == set()
    names = sorted(key.name for key in valid_keys)
    # two declarations, four registrations: the strategy's variant propagates
    assert names == ["strategy", "strategy", "summariser", "summariser"]
    assert len(Registry.retrieve_runnable_keys()) == 2


def test_tutorial_project_components_are_bound_correctly(reset_registry):
    Registry.build(directory=TUTORIAL / "07_project_layout")

    results = analyze_registry(Registry, deep=True)

    assert results, "nothing was analyzed"
    assert all(ok for ok, _, _ in results.values()), results


def test_tutorial_project_runs_end_to_end(reset_registry):
    """The runnable component produces a summary, not just a graph."""
    Registry.build(directory=TUTORIAL / "07_project_layout")

    key = next(
        key
        for key in Registry.retrieve_runnable_keys()
        if not key.tags  # the default configuration
    )
    summary = Registry.from_key(key).run()

    assert summary.endswith(".")
    assert summary.count(".") == 1  # the default keeps one sentence


# -- the scikit-learn example ------------------------------------------------


def test_examples_build(reset_registry):
    """The whole examples tree resolves, tutorial and pipeline together."""
    valid_keys, invalid_keys = Registry.build(directory=EXAMPLES)

    assert invalid_keys == set()
    assert {"examples", "tutorial/summarisation"} <= set(Registry._EXP_NAMESPACES)


def test_example_components_match_their_configurations(reset_registry):
    """Imports the pipeline components, so a broken binding cannot ship.

    Skipped when the `examples` extra is absent: these components need pandas
    and scikit-learn, and the point of the string binding is that a build does
    not.
    """
    pytest.importorskip("pandas")
    pytest.importorskip("sklearn")

    Registry.build(directory=EXAMPLES)
    results = analyze_registry(Registry, deep=True)

    failures = {key: errors for key, (ok, errors, _) in results.items() if not ok}
    assert not failures, failures


def test_example_demos_use_a_live_api(reset_registry):
    """Guards the specific rot that broke them: a call to a removed classmethod.

    Running the demos needs a dataset download, so this checks the thing that
    actually went wrong rather than the whole pipeline.
    """
    sources = [path.read_text() for path in (EXAMPLES / "demos").glob("*.py")]
    sources += [path.read_text() for path in (EXAMPLES / "components").glob("*.py")]

    assert sources
    callers = {
        match.group(1)
        for source in sources
        for match in re.finditer(r"(\w+)\.instantiate\(", source)
    }

    # Registry.instantiate is the live API; anything else calling .instantiate
    # is a component class, and that classmethod no longer exists.
    assert callers <= {"Registry"}, (
        f"{sorted(callers - {'Registry'})} call .instantiate, but "
        f"Component.instantiate was removed with the Component base class. "
        f"Use Registry.from_key or Registry.instantiate."
    )
