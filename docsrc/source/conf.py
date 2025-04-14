import sys
from pathlib import Path

sys.path.insert(0, Path(__file__).parent.parent.parent.resolve().absolute().as_posix())
sys.path.insert(0, Path(__file__).parent.parent.parent.resolve().absolute().joinpath('cinnamon').as_posix())
sys.path.insert(0, Path(__file__).parent.parent.parent.resolve().absolute().joinpath('cinnamon', 'utility').as_posix())

# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'Cinnamon'
copyright = '2025, Federico Ruggeri'
author = 'Federico Ruggeri'
release = '0.1'

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.napoleon',
    'sphinx.ext.autodoc',
    'sphinx.ext.githubpages',
    'sphinx_autodoc_typehints'
]

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
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_title = 'Cinnamon'
html_theme = 'sphinx_rtd_theme'
# html_theme_path = [sphinx_pdj_theme.get_html_theme_path()]
html_static_path = ['_static']
