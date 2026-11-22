"""An external directory that is a package never shadows the project.

``load_registrations`` used to put every directory it loaded first on
``sys.path``. External directories load after the project, so they ended up
ahead of it, and a package inside one shadowed the project's top-level package
of the same name: ``Registry.from_key`` then imported the external one and
failed to find the project's component in it.
"""

import sys
from pathlib import Path

import pytest

from cinnamon.registry import RegistrationKey, Registry
from cinnamon.utility.registration import qualified_package

PROJECT_REGISTRATIONS = """\
from cinnamon.configuration import Configuration, Param
from cinnamon.registry import RegistrationKey, Registry, register


class StudyConfig(Configuration):
    child: RegistrationKey = Param(RegistrationKey(name="child", namespace="lib"))


@register
def registrations():
    Registry.register_configuration(
        config=StudyConfig(),
        name="study",
        namespace="study",
        component="parts_pkg.parts.Project",
    )
"""

LIBRARY_REGISTRATIONS = """\
from cinnamon.configuration import Configuration
from cinnamon.registry import Registry, register

from .keys import NAMESPACE


@register
def registrations():
    Registry.register_configuration(
        config=Configuration(),
        name="child",
        namespace=NAMESPACE,
        component="lib.parts_pkg.parts.Other",
    )
"""


@pytest.fixture
def layout(tmp_path):
    """A project and an external package that both define ``parts_pkg``."""
    project = tmp_path / "project"
    (project / "configurations").mkdir(parents=True)
    (project / "configurations" / "regs.py").write_text(PROJECT_REGISTRATIONS)
    (project / "parts_pkg").mkdir()
    (project / "parts_pkg" / "__init__.py").write_text("")
    (project / "parts_pkg" / "parts.py").write_text(
        "class Project:\n    def __init__(self, child):\n        self.child = child\n"
    )

    library = tmp_path / "libroot" / "lib"
    (library / "configurations").mkdir(parents=True)
    (library / "__init__.py").write_text("")
    (library / "configurations" / "__init__.py").write_text("")
    (library / "configurations" / "keys.py").write_text('NAMESPACE = "lib"\n')
    (library / "configurations" / "regs.py").write_text(LIBRARY_REGISTRATIONS)
    (library / "parts_pkg").mkdir()
    (library / "parts_pkg" / "__init__.py").write_text("")
    (library / "parts_pkg" / "parts.py").write_text("class Other:\n    pass\n")

    yield project, library
    for name in [
        name
        for name in sys.modules
        if name.split(".")[0] in ("parts_pkg", "lib", "configurations")
    ]:
        sys.modules.pop(name, None)
    sys.path[:] = [entry for entry in sys.path if not entry.startswith(str(tmp_path))]


def test_a_package_inside_an_external_directory_does_not_shadow_the_project(
    layout, reset_registry
):
    project, library = layout

    Registry.build(directory=project, external_directories=[library])
    built = Registry.from_key(RegistrationKey(name="study", namespace="study"))

    assert type(built).__name__ == "Project"
    assert Path(sys.modules["parts_pkg"].__file__).parent.parent == project


def test_an_external_package_runs_under_its_qualified_name(layout, reset_registry):
    project, library = layout

    Registry.build(directory=project, external_directories=[library])

    # The relative import in the library's script resolved inside the library.
    assert "lib.configurations.keys" in sys.modules
    assert "configurations.keys" not in sys.modules
    assert str(library) not in sys.path


def test_an_external_package_that_is_not_importable_gets_its_parent_appended(
    layout, reset_registry
):
    project, library = layout

    Registry.build(directory=project, external_directories=[library])

    assert sys.path[-1] == str(library.parent)
    assert sys.path.index(str(project)) < sys.path.index(str(library.parent))

    Registry.initialize()
    assert str(library.parent) not in sys.path


def test_an_importable_external_package_adds_nothing_to_sys_path(
    layout, reset_registry
):
    project, library = layout
    sys.path.append(str(library.parent))

    Registry.build(directory=project, external_directories=[library])
    Registry.initialize()

    assert sys.path.count(str(library.parent)) == 1


def test_a_restored_snapshot_puts_an_appended_entry_back_at_the_end(
    tmp_path, reset_registry
):
    entry = str(tmp_path / "appended")
    Registry.add_to_sys_path(entry, append=True)
    state = Registry.snapshot()

    Registry.initialize()
    assert entry not in sys.path

    Registry.restore(state)
    try:
        assert sys.path[-1] == entry
    finally:
        sys.path.remove(entry)


def test_qualified_package_names_a_nested_package(tmp_path):
    nested = tmp_path / "top" / "inner"
    nested.mkdir(parents=True)
    (tmp_path / "top" / "__init__.py").write_text("")
    (nested / "__init__.py").write_text("")

    assert qualified_package(nested) == ("top.inner", tmp_path)


def test_qualified_package_refuses_what_cannot_be_imported(tmp_path):
    plain = tmp_path / "plain"
    plain.mkdir()
    invalid = tmp_path / "not-a-name"
    invalid.mkdir()
    (invalid / "__init__.py").write_text("")

    assert qualified_package(plain) is None
    assert qualified_package(invalid) is None
