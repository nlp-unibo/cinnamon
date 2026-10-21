"""
A library and a study built on it, in the arrangement downstream projects use.

cinnamon's own fixtures each build one layout at a time. Downstream projects
combine them: a library ships components and a ``configurations`` package, a
study ships another ``configurations`` package that subclasses the library's,
and a test session imports the library's classes once, at the top of a module,
then builds the registry again and again. Release 2.1.2 passed every test here
and still broke that arrangement, because no test here built it.

``examples/downstream`` is that arrangement, and this module drives it the way
a downstream suite does. A failure first seen in a downstream project belongs
here, as one more case over the same two packages.
"""

import multiprocessing
import os
import subprocess
import sys
from pathlib import Path

import pytest

from cinnamon import Registry

DOWNSTREAM = Path(__file__).resolve().parent.parent / "examples" / "downstream"
LIBRARY = DOWNSTREAM / "library"
STUDY = DOWNSTREAM / "study"
ABLATION = DOWNSTREAM / "ablation"

# A downstream suite imports its library before any build, as installed code.
sys.path.insert(0, str(DOWNSTREAM.parent))
import downstream.library.components  # noqa: E402
from downstream.ablation.configurations import keys as ablation_keys  # noqa: E402
from downstream.library.components import Encoder, Model, build_in_worker  # noqa: E402
from downstream.library.configurations import keys as library_keys  # noqa: E402
from downstream.study.configurations import keys as study_keys  # noqa: E402


def build_library():
    _, invalid = Registry.build(directory=LIBRARY)
    assert not invalid


def build_study():
    _, invalid = Registry.build(directory=STUDY, external_directories=[LIBRARY])
    assert not invalid


def test_the_entry_point_runs():
    """The study runs end to end in a fresh interpreter, as a user runs it."""
    result = subprocess.run(
        [sys.executable, str(DOWNSTREAM / "run.py")],
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert result.returncode == 0, result.stderr
    assert "'sizes': [4, 4, 4]" in result.stdout


@pytest.mark.parametrize("build", [build_library, build_study])
def test_the_caller_keeps_its_classes_across_builds(build, reset_registry):
    """Every build resolves the classes this module imported before the first.

    2.1.2 forgot every module under a scanned root, so the second build
    re-imported ``library.components`` and ``expected_type`` rejected the
    caller's own ``Model``. 2.2.1 fixed the same failure for a module first
    imported during a build.
    """
    module = downstream.library.components
    for _ in range(3):
        build()
        assert sys.modules["downstream.library.components"] is module
        model = Registry.from_key(library_keys.MODEL, expected_type=Model)
        assert isinstance(model.encoder, Encoder)


def test_a_class_first_imported_by_a_build_survives_the_next(reset_registry):
    """A library module a build imported is the caller's once the caller imports it.

    The library's configurations import ``downstream.library.heads``, and this
    module does not, so a build is what imports it. The caller then imports
    ``Head``. 2.2.0 forgot that module at the next build, as though the build
    still owned it, and ``expected_type`` rejected the caller's ``Head``.
    """
    build_library()
    from downstream.library.heads import Head  # noqa: PLC0415

    build_library()
    assert isinstance(Registry.from_key(library_keys.HEAD, expected_type=Head), Head)


def test_the_study_resolves_into_the_library(reset_registry):
    """The study's keys build library components with the study's values."""
    build_study()

    model = Registry.from_key(study_keys.MODEL, expected_type=Model)
    assert (model.depth, model.encoder.size) == (2, 4)
    assert Registry.from_key(library_keys.MODEL).depth == 1
    assert Registry.from_key(study_keys.TASK).run()["sizes"] == [4, 4, 4]


def test_each_project_sees_its_own_configurations(reset_registry):
    """Two ``configurations`` packages, built in turn, never resolve each other."""
    build_library()
    assert not Registry.in_registry(study_keys.TASK)

    build_study()
    assert Registry.in_registry(study_keys.TASK)

    build_library()
    assert not Registry.in_registry(study_keys.TASK)
    assert Registry.from_key(library_keys.TASK).run()["sizes"] == [4]


@pytest.mark.parametrize("relative", [False, True], ids=["absolute", "relative"])
def test_a_study_without_library_keys_builds_the_same_every_time(
    relative, reset_registry
):
    """Registrations an import pulled in come back on every build.

    The ablation imports the library's configuration module to subclass it,
    which runs the library's registrations, but names no library key. That
    module stayed in ``sys.modules`` after the first build, so the second
    import was a no-op and the library's keys were missing from every later
    build in the process.
    """
    # A relative external directory has to name the same root as the absolute
    # module files under it.
    library = Path(os.path.relpath(LIBRARY)) if relative else LIBRARY
    builds = []
    for _ in range(3):
        valid, invalid = Registry.build(
            directory=ABLATION, external_directories=[library]
        )
        assert not invalid
        builds.append({str(key) for key in valid})

    assert builds[0] == builds[1] == builds[2]
    assert Registry.in_registry(library_keys.MODEL)
    model = Registry.from_key(ablation_keys.MODEL, expected_type=Model)
    assert model.encoder.size == 1


def test_a_spawned_worker_builds_from_the_frozen_runtime(reset_registry):
    """A worker that scanned nothing builds a study model from the frozen registry."""
    build_study()
    runtime = Registry.freeze_runtime()

    with multiprocessing.get_context("spawn").Pool(1) as pool:
        size = pool.apply(build_in_worker, (runtime, study_keys.MODEL))

    assert size == 4
