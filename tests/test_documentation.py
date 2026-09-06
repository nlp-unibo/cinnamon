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
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docsrc" / "source"
TUTORIAL = ROOT / "examples" / "tutorial"
README = ROOT / "README.md"

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


#: Stubs that keep a retired URL working. GitHub Pages serves static files and
#: cannot issue a 301, so each is a zero-delay meta refresh.
REDIRECTS = DOCS / "_redirects"

REFRESH = re.compile(r'http-equiv="refresh"\s+content="0;\s*url=([^"]+)"')


def test_redirect_stubs_are_copied_into_the_build():
    """``html_extra_path`` is what puts the stubs in the output.

    Without it they are inert files in the source tree that no build ever looks
    at -- and the failure is silent, because a redirect nobody exercises looks
    exactly like a redirect that works.
    """
    conf = (DOCS / "conf.py").read_text()

    assert 'html_extra_path = ["_redirects"]' in conf, (
        "conf.py no longer copies _redirects/ into the build; every retired URL "
        "in that directory is now a 404"
    )


@pytest.mark.parametrize("stub", sorted(REDIRECTS.glob("*.html")), ids=lambda p: p.name)
def test_redirect_stub_points_at_a_page_that_exists(stub):
    """A redirect to a page that is also gone is worse than a 404.

    The target is checked against the *sources*, so this fails at test time
    rather than after a deploy.
    """
    match = REFRESH.search(stub.read_text())
    assert match, f"{stub.name} has no zero-delay meta refresh"

    target = match.group(1)
    assert not target.startswith(("http://", "https://")), (
        f"{stub.name} redirects to an absolute URL; use a relative one so the "
        f"stub works on either host name"
    )

    # "./" is the landing page; "foo.html" is the page built from "foo.rst".
    page = "index.rst" if target in ("./", ".", "") else target.replace(".html", ".rst")
    assert (DOCS / page).exists(), (
        f"{stub.name} redirects to {target}, which is built from {page} -- and "
        f"that source does not exist"
    )


def test_the_retired_overview_url_still_resolves():
    """The specific URL that moved, named so the reason is not lost.

    ``overview.rst`` became the landing page. The README, and anything else
    already pointing at ``/cinnamon/overview.html``, would otherwise 404.
    """
    assert (REDIRECTS / "overview.html").exists(), (
        "the overview redirect is gone; /cinnamon/overview.html now 404s"
    )


MD_PYTHON_BLOCK = re.compile(r"```python\n(.*?)```", re.DOTALL)


def test_the_readme_quickstart_runs(tmp_path):
    """The README's quickstart, executed rather than read.

    It is the first thing anyone sees, and nothing had ever run it. Two of its
    five steps did not work. Step 2 gave ``batch_size`` a default of 32 and then
    listed 32 among its ``variants``, which cinnamon rejects outright. Step 4
    called ``DataLoader.instantiate(...)``, a classmethod that died with the
    ``Component`` base class -- the same defect that broke both shipped demos,
    still sitting in the README a month later. Anyone following the page got a
    traceback at step 2 and another at step 4.

    Neither was reachable by the name checks above: ``DataLoader`` is the
    reader's class rather than ours, and a default colliding with a variant is a
    runtime error, not a missing name. Only running it finds this.

    The blocks are laid out on disk the way the README tells the reader to lay
    them out -- component in ``components.py``, registration under
    ``configurations/`` -- and then run in a subprocess, because ``Registry`` is
    class-level state and ``build`` scans the working directory.
    """
    readme = README.read_text()
    start = readme.index("## Quickstart")
    quickstart = readme[start : readme.index("## Key concepts", start)]

    blocks = MD_PYTHON_BLOCK.findall(quickstart)
    assert len(blocks) == 5, (
        f"expected the 5 quickstart steps, found {len(blocks)} python blocks "
        f"between '## Quickstart' and '## Key concepts'"
    )

    component, registration, build, instantiate, variants = blocks

    (tmp_path / "components.py").write_text(component)
    (tmp_path / "configurations").mkdir()
    (tmp_path / "configurations" / "__init__.py").write_text("")
    (tmp_path / "configurations" / "loader.py").write_text(registration)
    (tmp_path / "main.py").write_text(
        "from components import DataLoader\n"
        "from configurations.loader import DataLoaderConfig\n"
        f"{build}\n{instantiate}\n{variants}\n"
        "print('quickstart ok')\n"
    )

    result = subprocess.run(
        [sys.executable, "main.py"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert result.returncode == 0, (
        f"the README quickstart does not run:\n{result.stderr}"
    )
    assert "quickstart ok" in result.stdout


#: Links from the README into the documentation site. The README is rendered by
#: GitHub, outside the site, so these have to be absolute -- the ``:doc:`` rule
#: that applies inside ``docsrc`` cannot help here.
README_DOC_LINK = re.compile(
    r"https://nlp-unibo\.github\.io/cinnamon/([A-Za-z0-9_/]*\.html)?"
)


def test_readme_links_into_the_docs_point_at_pages_that_exist():
    """Every documentation link in the README resolves to a real page.

    Nothing checked these, and one of them rotted exactly as you would expect:
    the "Documentation" link pointed at ``overview.html`` for as long as it took
    someone to click it after that page became the landing page. Inside
    ``docsrc`` the fix is ``:doc:``, which Sphinx validates. The README is
    rendered by GitHub and cannot use it, so the check lives here instead.
    """
    missing = []
    for target in README_DOC_LINK.findall(README.read_text()):
        if not target:  # the site root, which is index.rst
            continue
        source = DOCS / target.replace(".html", ".rst")
        redirect = REDIRECTS / target
        if not source.exists() and not redirect.exists():
            missing.append(target)

    assert not missing, (
        f"README links to documentation pages that do not exist: {sorted(set(missing))}"
    )


#: An install instruction naming a distribution, in markdown or rst.
INSTALL_COMMAND = re.compile(r"pip install \"?([A-Za-z0-9_./\[\],-]+)\"?")

#: Everything that is not a distribution name: the editable and local-path forms
#: used when working on cinnamon itself, and the tooling the docs tell you to
#: install alongside it.
NOT_A_DISTRIBUTION = {"-e", ".", "./cinnamon", "nox", "--upgrade"}


def test_documented_installs_name_the_right_distribution():
    """``pip install cinnamon`` fetches somebody else's project.

    The distribution is ``cinnamon-core``. ``cinnamon`` on PyPI is an unrelated
    data-drift monitoring tool, so every ``pip install cinnamon`` in the README,
    the landing page, the tutorial and the command reference sent readers to the
    wrong library -- and then to an ``ImportError``, since that project has no
    ``cinnamon.registry``.

    Nothing could have caught this from inside the repository: the name was
    consistent everywhere, self-consistent, and wrong. It took looking at PyPI.
    The check exists so the answer stays looked-up rather than re-derived.
    """
    wrong = []
    for path in [README, *RST_FILES, ROOT / "CONTRIBUTING.md"]:
        for match in INSTALL_COMMAND.findall(path.read_text()):
            name = match.split("[")[0]
            if name in NOT_A_DISTRIBUTION or not name:
                continue
            if name != "cinnamon-core":
                wrong.append(f"{path.name}: pip install {match}")

    assert not wrong, (
        "the distribution is cinnamon-core; 'cinnamon' on PyPI is an unrelated "
        f"project: {sorted(set(wrong))}"
    )


def test_the_typed_marker_is_shipped():
    """``Typing :: Typed`` is a claim; ``py.typed`` is what backs it.

    Without the marker file a type checker ignores the annotations in an
    installed package, so the classifier would promise something the wheel does
    not deliver.
    """
    pyproject = (ROOT / "pyproject.toml").read_text()

    if "Typing :: Typed" in pyproject:
        assert (ROOT / "cinnamon" / "py.typed").exists(), (
            "pyproject claims Typing :: Typed but cinnamon/py.typed is missing"
        )
        assert 'cinnamon = ["py.typed"]' in pyproject, (
            "cinnamon/py.typed exists but is not declared as package-data, so it "
            "is not in the wheel"
        )


def test_the_docs_do_not_restate_the_version():
    """``conf.py`` reads the version rather than repeating it.

    It said ``release = "0.1"`` while the package said 1.1.0, so every built page
    carried a version number that had been wrong for four releases. Nothing
    noticed, because a wrong-but-syntactically-fine string breaks no build.

    ``pyproject.toml`` already reads ``cinnamon.__version__``. This makes the
    docs read it too, so there is one place to change at release time instead of
    three that must be remembered together.
    """
    conf = (DOCS / "conf.py").read_text()

    assert "release = cinnamon.__version__" in conf, (
        "conf.py should read the version from the package, not restate it"
    )
    assert not re.search(r'release\s*=\s*["\']', conf), (
        "conf.py hardcodes a version string again"
    )
