import sys
from pathlib import Path

base_path = Path(__file__).parent.parent.parent.resolve().absolute()
sys.path.insert(0, base_path.as_posix())
sys.path.insert(
    0,
    base_path.joinpath("cinnamon").as_posix(),
)
sys.path.insert(
    0,
    base_path.joinpath("cinnamon", "utility").as_posix(),
)
sys.path.insert(
    0,
    base_path.joinpath("examples").as_posix(),
)

# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "Cinnamon"
copyright = "2025, Federico Ruggeri"
author = "Federico Ruggeri"
# Read from the package rather than restated here. This said "0.1" while the
# package said 1.1.0, so every built page carried a version number that had been
# wrong for four releases. pyproject reads the same attribute, so there is one
# place to change.
#
# The import cannot go at the top of the file: it only resolves once the
# sys.path entries above are in place.
import cinnamon  # noqa: E402

release = cinnamon.__version__
version = release

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.napoleon",
    "sphinx.ext.autodoc",
    "sphinx.ext.githubpages",
    "sphinx_autodoc_typehints",
]

# ``InquirerPy`` is an optional dependency: it ships with the ``cli`` extra, and
# cinnamon.cli / cinnamon.utility.inquirer import it at module level. Autodoc has
# to import a module to document it, so without the extra those two imports fail
# -- and since the build treats warnings as errors, the whole thing stops.
#
# Mock it only when it is really missing, so an environment that has it still
# documents the real signatures.
try:
    import InquirerPy  # noqa: F401
except ImportError:  # pragma: no cover - depends on the install extras
    autodoc_mock_imports = ["InquirerPy"]

# Napoleon settings
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_preprocess_types = False
napoleon_type_aliases = None
napoleon_attr_annotations = True

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_title = "Cinnamon"
html_theme = "sphinx_rtd_theme"
# html_theme_path = [sphinx_pdj_theme.get_html_theme_path()]
# No custom assets yet; an entry for a missing directory only warns.
html_static_path = []

# Files copied verbatim into the build root, on top of the generated pages.
#
# Holds redirect stubs for pages that have moved: GitHub Pages serves static
# files and cannot issue a 301, so a zero-delay meta refresh is the available
# mechanism. To retire another URL, add ``<old-name>.html`` to that directory
# rather than leaving the address to 404.
html_extra_path = ["_redirects"]
