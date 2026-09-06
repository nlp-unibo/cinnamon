"""
The documentation has to describe the library that exists.

It drifted badly once: an entire page documented a ``Component`` base class that
had been deleted, told readers to inherit from it, and described
``Registry.instantiate_component`` and ``Component.instantiate`` -- neither of
which existed. Following that page produced code that could not run.

Sphinx does not catch any of this. It renders prose faithfully whether or not
the API is real, and an ``automodule`` for a deleted module is a warning that
scrolls past. These tests check the two things that actually rot: the names the
documentation uses, and whether its code is even syntactically Python.
"""

import ast
import importlib
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docsrc" / "source"
TUTORIAL = ROOT / "examples" / "tutorial"

#: Classes whose attributes the documentation refers to by name.
DOCUMENTED_CLASSES = {
    "Registry": "cinnamon.registry",
    "RegistrationKey": "cinnamon.registry",
    "Configuration": "cinnamon.configuration",
}

CODE_BLOCK = re.compile(
    r"\.\. code-block:: python\n\n((?:(?:[ \t]+[^\n]*)?\n)+)", re.MULTILINE
)
API_REFERENCE = re.compile(
    r"\b(" + "|".join(DOCUMENTED_CLASSES) + r")\.([a-z_][a-z0-9_]*)\b"
)
CINNAMON_IMPORT = re.compile(r"^\s*from (cinnamon[.\w]*) import ([^\n]+)", re.MULTILINE)

RST_FILES = sorted(DOCS.rglob("*.rst"))


def test_documentation_sources_are_present():
    assert RST_FILES, f"no .rst files under {DOCS}"


@pytest.mark.parametrize("path", RST_FILES, ids=lambda p: p.name)
def test_documented_api_names_exist(path):
    """Every ``Registry.foo`` the docs mention is a real attribute.

    This is the check that would have caught ``Registry.instantiate_component``
    and ``Component.instantiate``.
    """
    missing = []
    for owner, attribute in API_REFERENCE.findall(path.read_text()):
        cls = getattr(importlib.import_module(DOCUMENTED_CLASSES[owner]), owner)
        if not _has_member(cls, attribute):
            missing.append(f"{owner}.{attribute}")

    assert not missing, (
        f"{path.name} documents names that do not exist: {sorted(set(missing))}"
    )


@pytest.mark.parametrize("path", RST_FILES, ids=lambda p: p.name)
def test_documented_imports_resolve(path):
    """``from cinnamon.x import Y`` in the docs must actually import.

    This is the check that would have caught ``from cinnamon.component import
    Component`` surviving the removal of that module.
    """
    problems = []
    for module_name, imported in CINNAMON_IMPORT.findall(path.read_text()):
        try:
            module = importlib.import_module(module_name)
        except ImportError:
            problems.append(f"no module {module_name}")
            continue
        for name in (part.strip() for part in imported.split(",")):
            if name and not hasattr(module, name):
                problems.append(f"{module_name} has no {name}")

    assert not problems, f"{path.name}: {problems}"


@pytest.mark.parametrize("path", RST_FILES, ids=lambda p: p.name)
def test_python_code_blocks_parse(path):
    """Every python code block is syntactically valid.

    Fragments are expected -- a block may reference names defined elsewhere on
    the page -- so this parses rather than executes. It still catches the
    mangled indentation and truncated snippets that editing prose tends to
    produce.
    """
    failures = []
    for index, block in enumerate(CODE_BLOCK.findall(path.read_text()), start=1):
        source = _dedent(block)
        if not source.strip():
            continue
        try:
            ast.parse(source)
        except SyntaxError as error:
            failures.append(f"block {index}: {error.msg} (line {error.lineno})")

    assert not failures, f"{path.name}: {failures}"


def _has_member(cls: type, attribute: str) -> bool:
    """True for methods, class attributes, annotated instance attributes and fields.

    A bare annotation -- ``metadata: str | None`` in a class body -- declares a
    real instance attribute without creating a class one, so ``hasattr`` alone
    would call it undocumented.
    """
    if hasattr(cls, attribute):
        return True
    if attribute in getattr(cls, "model_fields", {}):
        return True
    return any(
        attribute in getattr(base, "__annotations__", {}) for base in cls.__mro__
    )


def _dedent(block: str) -> str:
    lines = [line for line in block.splitlines() if line.strip()]
    if not lines:
        return ""
    indent = min(len(line) - len(line.lstrip()) for line in lines)
    return "\n".join(line[indent:] for line in block.splitlines())


def test_no_page_documents_the_removed_component_base_class():
    """A targeted guard for the specific drift that happened.

    ``Component`` was a base class users had to inherit from. It was removed;
    components are plain classes. Prose saying otherwise is wrong in a way the
    name checks above cannot see, because it never names an attribute.
    """
    offenders = [
        path.name
        for path in RST_FILES
        if re.search(
            r"\(Component\)|cinnamon\.component|inherit from ``Component``",
            path.read_text(),
        )
    ]

    assert not offenders, (
        f"pages still describe the removed Component base class: {offenders}"
    )


def test_every_tutorial_step_has_a_documentation_page():
    """The tutorial section covers every step that exists in the repository.

    The pages pull their code in with ``literalinclude``, so a *renamed* file
    breaks the docs build and is caught. An *added* one is the silent case: the
    new step ships, no page mentions it, and the section quietly stops being the
    tutorial. Sphinx cannot see that, because nothing is broken -- there is just
    less than there should be.
    """
    steps = sorted(path.name for path in TUTORIAL.glob("[0-9][0-9]_*"))
    assert steps, f"no tutorial steps found under {TUTORIAL}"

    included = "\n".join(
        path.read_text() for path in (DOCS / "tutorial").rglob("*.rst")
    )

    undocumented = [step for step in steps if step not in included]

    assert not undocumented, (
        f"tutorial steps with no documentation page: {undocumented}. "
        f"Add a page under docsrc/source/tutorial/ that literalincludes each one."
    )


def test_tutorial_pages_point_at_files_that_exist():
    """Every ``literalinclude`` path in the docs resolves.

    Sphinx already fails the build on a missing include, but only when the docs
    are built. This says the same thing in the test suite, where it is cheap and
    fails with the offending path rather than a build log.
    """
    missing = []
    for page in DOCS.rglob("*.rst"):
        for target in re.findall(r"\.\. literalinclude:: (\S+)", page.read_text()):
            if not (page.parent / target).resolve().exists():
                missing.append(f"{page.relative_to(DOCS)} -> {target}")

    assert not missing, f"literalinclude targets that do not exist: {missing}"


#: Any way of spelling "this documentation site". Both host names serve it --
#: the github.io address 301s to the unibo one.
SELF_LINK = re.compile(
    r"https?://[^\s`<>]*(?:nlp-unibo\.github\.io|nlp\.unibo\.it)/cinnamon/[^\s`<>]+"
)


def test_the_docs_do_not_link_to_themselves_by_absolute_url():
    """Internal references must be ``:doc:`` so Sphinx can check them.

    An absolute link to our own site looks identical in the rendered page and is
    invisible to ``-W``: Sphinx never resolves it, so renaming or removing the
    target produces a 404 that no build, test or review will catch. That is not
    hypothetical -- the README pointed at ``overview.html`` for as long as it
    took someone to click it after the page was folded into the landing page,
    and four concept pages linked to each other the same way.

    ``:doc:`` gets validated at build time and rewritten to the right relative
    path on every page, so this is strictly better as well as safer.
    """
    offenders = []
    for path in RST_FILES:
        for match in SELF_LINK.findall(path.read_text()):
            offenders.append(f"{path.relative_to(DOCS)}: {match}")

    assert not offenders, (
        "documentation links to itself by absolute URL; use :doc:`page` instead "
        f"so Sphinx validates it: {offenders}"
    )
